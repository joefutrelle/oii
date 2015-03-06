import sys
import operator
import os
from urllib2 import urlopen
from StringIO import StringIO
from lxml import etree
import re
from glob import iglob
import fileinput
import csv
import json
import logging

import traceback

from oii.utils import coalesce, asciitable, structs
from oii.jsonquery import jsonquery
from oii.utils import memoize, search_path

class UnboundVariable(Exception):
    pass

@memoize
def compile_regex(pattern):
    return re.compile(pattern)

# pretty-print bindings
def pprint(bindings,header=''):
    if len(bindings) == 0:
        print '%s {}' % header
        return
    if len(bindings) == 1:
        print '%s %s' % (header, bindings)
        return
    # remove integer bindings (groups from the most recent regex match)
    for var in bindings.keys():
        try:
            int(var)
            del bindings[var]
        except ValueError:
            pass
    # colon-align
    width = max(len(var) for var in bindings)
    print '%s {' % header
    for var in sorted(bindings):
        print '%s%s: "%s"' % (' ' * (width-len(var)),var,bindings[var])
    print '}'

# foo.bar corresponds to an XPath of /namespace[@name='foo']/rule[@name='bar']
def find_names(e):
    def descend(e,namespace=[]):
        if e.tag=='namespace':
            sub_ns = namespace + [e.get('name')]
            for se in e:
                for name, name_e in descend(se,namespace=sub_ns):
                    yield name, name_e
        elif e.tag=='rule':
            yield namespace + [e.get('name')], e
    return dict(('.'.join(n),ne) for n, ne in descend(e))

LDR_INTERP_PATTERN = re.compile(r'([^\$]*)(\$\{([a-zA-Z0-9_.]+)\})')
LDR_WS_SEP_REGEX = r'\s+'
LDR_WS_SEP_PATTERN = re.compile(LDR_WS_SEP_REGEX)

# supports time-like regexes e.g., IFCB9_yyyy_YYY_HHMMSS
def timestamp2regex(pattern):
    # FIXME handle unfortunate formats such as
    # - non-zero-padded numbers
    # - full and abbreviated month names
    pattern = re.sub(r'(([0-9])\2*)',r'(?P<n\2>[0-9]+)',pattern) # fixed-length number eg 111 88
    pattern = re.sub(r's+','(?P<sss>[0-9]+)',pattern) # milliseconds
    pattern = re.sub(r'yyyy','(?P<yyyy>[0-9]{4})',pattern) # four-digit year
    pattern = re.sub(r'mm','(?P<mm>0[1-9]|1[0-2])',pattern) # two-digit month
    pattern = re.sub(r'dd','(?P<dd>0[1-9]|[1-2][0-9]|3[0-1])',pattern) # two-digit day of month
    pattern = re.sub(r'YYY','(?P<YYY>[0-3][0-9][0-9])',pattern) # three-digit day of year
    pattern = re.sub(r'HH','(?P<HH>[0-1][0-9]|2[0-3])',pattern) # two-digit hour
    pattern = re.sub(r'MM','(?P<MM>[0-5][0-9])',pattern) # two-digit minute
    pattern = re.sub(r'SS','(?P<SS>[0-5][0-9])',pattern) # two-digit second
    pattern = re.sub(r'#','[0-9]+',pattern) # any string of digits (non-capturing)
    pattern = re.sub(r'i','[a-zA-Z][a-zA-Z0-9_]*',pattern) # an identifier (e.g., jpg2000) (non-capturing)
    pattern = re.sub(r'\.ext',r'(?:.(?P<ext>[a-zA-Z][a-zA-Z0-9_]*))',pattern) # a file extension
    pattern = re.sub(r'\.',r'\.',pattern) # a literal '.'
    pattern = re.sub(r'\\.','.',pattern) # a regex '.'
    pattern = re.sub(r'any','.*',pattern) # a regex .*
    return pattern

def flatten(dictlike, include=None, exclude=None):
    # an appropriate copy operation. this WILL NOT COPY internal dicts or lists
    result = dict(dictlike.items())
    if include is not None:
        for k in result.keys():
            if k not in include:
                del result[k]
    if exclude is not None:
        for k in result.keys():
            if k in exclude:
                del result[k]
    return result

# substitute patterns like ${varname} for their values given
# scope = values for the names (dict-like)
# e.g., interpolate('${x}_${blaz}',{'x':'7','bork':'z','blaz':'quux'}) -> '7_quux'
#import jinja2
def interpolate(template,scope,fail_fast=True):
    if not '$' in coalesce(template,''):
        return template
    s = StringIO()
    end = 0
    for m in re.finditer(LDR_INTERP_PATTERN,template):
        end = m.end()
        (plain, expr, key) = m.groups()
        s.write(plain)
        try:
            s.write(scope[key])
        except KeyError:
            if fail_fast:
                raise UnboundVariable(key)
    s.write(template[end:])
    interpolated = s.getvalue()
#    interpolated = jinja2.Environment().from_string(interpolated).render(**scope.flatten())
    return interpolated

## interpolate a template using Jinja2
#def interpolate(template,scope):
#    return jinja2.Environment().from_string(template).render(**scope.flatten())

class ScopedExpr(object):
    def __init__(self,elt,bindings={}):
        self.elt = elt
        self.bindings = bindings
    def get(self,attr_name):
        template = self.elt.get(attr_name)
        if template is None:
            return None
        return interpolate(template, self.bindings)
    def get_list(self,attr_name,delim=None):
        delim = coalesce(delim, LDR_WS_SEP_PATTERN)
        templates = re.split(delim, self.elt.get(attr_name))
        return map(lambda t: interpolate(t,self.bindings), templates)
    @property
    def tag(self):
        return self.elt.tag
    def findall(self,tagname):
        return self.elt.findall(tagname)
    @property
    def text(self):
        return interpolate(self.elt.text, self.bindings)
    @property
    def raw_text(self):
        return self.elt.text
    def __iter__(self):
        return self.elt.__iter__()
    def __repr__(self):
        return '<%s/>' % self.tag

def eval_test(value,op,test_value):
    op_fn = getattr(operator,op)
    try:
        return op_fn(float(value),float(test_value))
    except ValueError:
        return op_fn(value,test_value)
    return False

# utility to parse "vars" argument
def parse_vars_arg(expr,attr='vars'):
    var_name_list = expr.get(attr)
    if var_name_list:
        return [var for var in re.split(LDR_WS_SEP_PATTERN,var_name_list) if var != '']
    return None

# utility to parse single var argument, which always defaults to '_'
def parse_var_arg(expr,attr='var'):
    return coalesce(expr.get(attr),'_')

# utility to parse a source file or url and get a stream
def parse_source_arg(expr):
    url = expr.get('url')
    file_path = coalesce(expr.get('file'),'-')
    return url, file_path

def open_source_arg(url=None, file_arg=None):
    if url is not None:
        return urlopen(url)
    elif file_arg is not None:
        return open(file_arg)
    else:
        raise ValueError

# filter out (and optionally count) distinct solutions. if vars is specified,
# retain only those vars prior to testing for uniqueness.
# if expr is specified parse the 'distinct' argument from it
# to get the var list.
# if neither is specified, allow all solutions
def with_distinct(solution_generator,distinct=None):
    distinct_solutions = set()
    for raw_solution in solution_generator:
        solution = flatten(raw_solution,distinct)
        f_solution = frozenset(solution.items())
        if f_solution not in distinct_solutions:
            distinct_solutions.add(f_solution)
            yield solution

# count is used to specify variable to hold the 1-based distinct/nondistinct
# solution count.
# nth is used to select a specific solution by solution number and ignore the rest
def with_count(solution_generator,count=None,nth=None):
    c = 1
    for s in solution_generator:
        if count is not None:
            s[count] = c
        if nth is not None:
            if c==nth:
                yield s
                return
        else:
            yield s
        c += 1

# apply aliasing to a solution generator.
# if expr is specified parse the "rename" and "as" arguments from
# it to get the aliases dict.
# if neither is specified allow all solutions
def with_aliases(solution_generator,aliases={}):
    for raw_solution in solution_generator:
        s = {}
        for k,v in raw_solution.items():
            try:
                if k in aliases: s[aliases[k]] = v
                else: s[k] = v
            except KeyError:
                raise KeyError('unbound variable %s' % k)
        yield s

# apply block-level include/excludes
def with_inc_exc(solution_generator,include=None,exclude=None):
    for raw_solution in solution_generator:
        s = flatten(raw_solution,include,exclude)
        yield s

# apply block-level modifications such as distinct, rename, include/exclude, count, and nth
def with_block(S,expr,bindings={}):
    return with_post_block(with_pre_block(S,expr,bindings),expr,bindings)

# apply block-level modifications *before* the inner block produces solutions
def with_pre_block(S,expr,bindings={}):
    bindings = flatten(bindings)
    # include/exclude
    include = parse_vars_arg(expr,'include')
    exclude = parse_vars_arg(expr,'exclude')
    if include is not None or exclude is not None:
        S = with_inc_exc(S,include,exclude)
    # rename/as
    rename = parse_vars_arg(expr,'rename')
    rename_as = parse_vars_arg(expr,'as')
    try:
        aliases = dict((o,n) for o,n in zip(rename,rename_as))
        S = with_aliases(S,aliases)
    except TypeError:
        pass
    # now yield from the stack of solution generators
    for s in S:
        yield s

# apply block-level modifiers *after* the inner block produces solutions
def with_post_block(S,expr,bindings={}):
    bindings = flatten(bindings)
    # distinct
    distinct = parse_vars_arg(expr,'distinct')
    if distinct is not None:
        S = with_distinct(S,distinct)
    # count
    count = expr.get('count')
    nth = expr.get('nth')
    if nth is not None:
        nth = int(nth)
    if count is not None or nth is not None:
        S = with_count(S,count,nth)
    # now yield from the stack of solution generators
    for s in S:
        yield s

# evaluate a block of expressions using recursive descent to generate and filter
# solutions a la Prolog
def evaluate_block(exprs,bindings={},global_namespace={}):
    # utility to parse arguments to match and split
    def parse_match_args(expr,bindings,default_pattern='.*'):
        if expr.get('value'):
            value = expr.get('value')
        else:
            var_arg = parse_var_arg(expr)
            try:
                value = str(bindings[var_arg])
            except KeyError: # the caller is attempting to match an unbound variable
                raise UnboundVariable(var_arg)
        timestamp = expr.get('timestamp')
        if timestamp is not None:
            pattern = timestamp2regex(timestamp)
        else:
            pattern = coalesce(expr.get('pattern'),default_pattern)
        return pattern, value
    # utility block evaluation function using this expression's bindings and global namespace
    def local_block(exprs,inner_bindings={}):
        bb = dict(bindings.items()) # an appropriate copy operation
        bb.update(inner_bindings)
        return evaluate_block(exprs,bb,global_namespace)
    # utility recurrence expression establishes an inner scope and evaluates
    # the remaining expressions (which will yield solutions to the head expression)
    # usage: for s in rest(expr,bindings): yield s
    def rest(expr,inner_bindings={}):
        # this is where we have an opportunity to discard variables before recurring
        # based on this expression
        discard = set()
        if expr.get('retain'):
            discard = set(bindings.keys()).difference(set(parse_vars_arg(expr,'retain')))
        for ss in local_block(exprs[1:],inner_bindings):
            yield flatten(ss,exclude=discard)
    # utility recurrence expression for unnamed block
    # accepts either a solution generator which produces inner bindings for the inner block,
    # or simply a single set of bindings (the outer bindings)
    def inner_block(expr,inner_bindings={},solution_generator=None):
        if solution_generator is None:
            S = with_block(local_block(list(expr),inner_bindings),expr,bindings)
        else:
            # wrap the solution generator in with_block
            def SS():
                for s in with_pre_block(solution_generator,expr,bindings):
                    for ss in local_block(list(expr),s):
                        yield ss
            S = with_post_block(SS(),expr,bindings)
        # now recur
        for s in S:
            for ss in rest(expr,s):
                yield ss
    # terminal case; we have arrived at the end of the block with a solution, so yield it
    if len(exprs)==0:
        yield flatten(bindings)
        return
    # handle the first expression
    # wrap in interpolation wrapper that interpolates all arguments
    expr = ScopedExpr(exprs[0], bindings)
    # The miss expression indicates no match has been found.
    # So refuse to recur, will not yield any solutions
    if expr.tag=='miss':
        return
    # The hit expression means a match has been found.
    # So yield the current set of bindings.
    # <hit/>
    # it is also an implicit block supporting block-level modifiers,
    # and generates a hit for every solution of that inner block
    elif expr.tag=='hit':
        for s in with_block(local_block(list(expr)),expr,bindings):
            yield s
            for ss in rest(expr,s):
                yield ss
    # Invoke means descend, once, into a named rule, evaluating it as a block,
    # with the current bindings in scope, and recur for each of its solutions.
    # options include filtering the input variables, including
    # all block level operations e.g., distinct and rename/as
    # <invoke rule="{name}" [using="{var1} {var2}"]/>
    elif expr.tag=='invoke':
        rule_name = expr.get('rule')
        using = parse_vars_arg(expr,'using')
        args = flatten(bindings,using)
        S = invoke(rule_name,args,global_namespace)
        for s in inner_block(expr,bindings,S):
            yield s
    # The var expression sets variables to interpolated values
    # <var name="{name}">{value}</var>
    # or
    # <var name="{name}">
    #   <val>{value1}</val>
    #   <val>{value2}</val>
    # </var>
    elif expr.tag=='var':
        var_name = parse_var_arg(expr,'name')
        sub_val_exprs = expr.findall('val')
        try:
            if len(sub_val_exprs) == 0:
                var_val = expr.text
                for s in rest(expr,{var_name:var_val}):
                    yield s
            else:
                for sub_val_expr in sub_val_exprs:
                    var_val = ScopedExpr(sub_val_expr, bindings).text
                    for s in rest(expr,{var_name:var_val}):
                        yield s
        except UnboundVariable, uv:
            logging.warn('var %s: unbound variable in template "%s": %s' % (var_name, expr.raw_text, uv))
            return # miss
    # The vars expression is the plural of var, for multiple assignment
    # with any regex as a delimiter between variable values.
    # <vars names="{name1} {name2} [delim="{delim}"]>{value1}{delim}{value2}</vars>
    # or
    # <vars names="{name1} {name2} [delim="{delim}"]>
    #   <vals>{value1}{delim}{value2}</vals>
    #   <vals>{value1}{delim}{value2}</vals>
    # </vars>
    elif expr.tag=='vars':
        try:
            var_names = re.split(LDR_WS_SEP_PATTERN,expr.get('names'))
            sub_val_exprs = expr.findall('vals')
            delim = coalesce(expr.get('delim'),LDR_WS_SEP_PATTERN)
            if len(sub_val_exprs) == 0:
                var_vals = map(lambda t: interpolate(t,bindings), re.split(delim,expr.raw_text))
                for s in rest(expr,dict(zip(var_names,var_vals))):
                    yield s
            else:
                for sub_val_expr in sub_val_exprs:
                    sub_val_expr = ScopedExpr(sub_val_expr, bindings)
                    var_vals = map(lambda t: interpolate(t,bindings), re.split(delim,sub_val_expr.raw_text))
                    for s in rest(expr,dict(zip(var_names,var_vals))):
                        yield s
        except UnboundVariable, uv:
            logging.warn('vars: unbound variable %s' % uv)
            return # miss
    # all is a conjunction. it is like an unnamed namespace block
    # and will yield any solution that exists after all exprs are evaluated
    # in sequence
    # <all>
    #   {expr1}
    #   {expr2}
    #   ...
    #   {exprn}
    # </all>
    elif expr.tag=='all':
        for s in inner_block(expr):
            yield s
    # any is a disjunction. it will yield all solutions of each expr
    # <any>
    #   {expr1}
    #   {expr2}
    #   ...
    #   {exprn}
    # </any>
    # first is like any except it only yields the solutions of the first clause that produces any
    # <first>
    #   {expr1}
    #   {expr2}
    #   ...
    #   {exprn}
    # </first>
    elif expr.tag in ('any','first'):
        for sub_expr in list(expr): # iterate over subexpressions
            done = False
            for s in local_block([sub_expr]): # treat each one as a block
                for ss in rest(expr,s):  # and recur for each of its solutions
                    done = True
                    yield ss
            if done and expr.tag=='first': # if all we want is the first subexpr
                return # then stop
    # none is negation. if the enclosed block generates any solutions,
    # this will generate a miss rather than a hit. otherwise it will recur.
    # <none>
    #   {expr1}
    #   {expr2}
    #   ...
    #   {exprn}
    # </none>
    elif expr.tag=='none':
        for s in inner_block(expr):
            return # miss
        # if we fell through, there were no solutions
        for s in rest(expr):
            yield s
    # log interpolates its text and prints it. useful for debugging
    # <log>{template}</log>
    elif expr.tag=='log':
        print expr.text
        for s in rest(expr):
            yield s
    # match generates solutions for every regex match
    # <match [pattern="{regex}"|timestamp="{date pattern}"] [value="{template}"|var="{variable to match}"] [groups="{name1} {name2}"] [optional="true/false"/>
    # if "value" is specified, the template is interpolated and then matched against,
    # if "var" is specified, the variable's value is looked up and then matched.
    # var="foo" is equivalent to value="${foo}"
    # if pattern is not specified the default pattern is ".*"
    # match also acts as an implicit, unnamed block supporting block-level modifiers.
    elif expr.tag=='match':
        optional = expr.get('optional')
        optional = optional is not None and optional in ['true', 'True', 'yes', 'Yes']
        m = False
        try:
            pattern, value = parse_match_args(expr,bindings,'.*')
            group_name_list, group_names = expr.get('groups'), []
            if group_name_list:
                group_names = re.split(LDR_WS_SEP_PATTERN,group_name_list)
            p = compile_regex(pattern)
            m = p.match(value)
        except UnboundVariable, uv:
            if not optional:
                logging.warn('match: unbound variable %s' % uv)
                return # miss
        if m:
            groups = m.groups()
            named_ixs = p.groupindex.values()
            groups_minus_named = [n for n in range(len(groups)) if n+1 not in named_ixs]
            inner_bindings = {}
#            print 'pattern = %s' % pattern
#            print 'groups = %s' % (groups,)
#            print 'group names = %s' % group_names
#            print 'named_ixs = %s' % named_ixs
#            print 'gmn = %s' % groups_minus_named
#            print 'groupindex = %s' % p.groupindex
#            print 'groupdict = %s' % m.groupdict()
            # bind user-specified groups to group names
            for name,n in zip(group_names, groups_minus_named):
                try:
                    if groups[n] is not None:
                        inner_bindings[name] = groups[n]
                except IndexError:
                    pass # innocuous
            # bind pattern-specified groups to group names
            for name,group in m.groupdict().items():
                if group is not None:
                    inner_bindings[name] = group
            # now invoke the (usually empty) inner unnamed block and recur
            for s in inner_block(expr,inner_bindings):
                yield s
        elif optional:
            for s in rest(expr):
                yield s
        else:
            return # miss
    # test performs equality and inequality tests over strings and numbers
    # <test [var={var}|value={template}] [eq|gt|lt|ge|le|ne]={template}/>
    # and is also an implicit block.
    elif expr.tag=='test':
        try:
            var = expr.get('var')
            value = expr.get('value')
            if value is None:
                value = bindings[var]
        except KeyError:
            logging.warn('test: unbound variable %s' % var)
            return # miss
        except UnboundVariable, uv:
            logging.warn('test: unbound variable %s' % uv)
            return # miss
        op = coalesce(*[a for a in ['eq','gt','lt','ge','le','ne'] if expr.get(a)])
        tv = expr.get(op)
        if eval_test(value,op,tv): # hit
            for s in inner_block(expr):
                yield s
        else:
            return # miss
    # split iterates over the result of splitting a value by a regex, assigning it repeatedly
    # to the variable specified by group. like match it recurs and is also an implicit block
    # <split [var="{var}"|value="{template}"] [pattern="{pattern}"] [group="{name}|vars="{name1} {name}"]/>
    # if pattern is not specified the default pattern is "  *"
    # alternatively one can use split to do multiple assignment, as in this example
    # <split value="foo bar baz" vars="a b c"/>
    # which will set a=foo, b=bar, c=baz
    elif expr.tag=='split':
        try:
            pattern, value = parse_match_args(expr,bindings,default_pattern=LDR_WS_SEP_REGEX)
        except UnboundVariable, uv:
            logging.warn('split: unbound variable %s' % uv)
            return # miss
        var_names = parse_vars_arg(expr)
        group = expr.get('group')
        if group:
            def S():
                for val in re.split(pattern,value):
                    yield {group: val}
            # now invoke the (usually empty) inner unnamed block and recur
            for s in inner_block(expr,solution_generator=S()):
                yield s
        elif var_names:
            inner_bindings = dict((n,v) for n,v in zip(var_names, re.split(pattern,value)))
            # now invoke the (usually empty) inner unnamed block and recur
            for s in inner_block(expr,inner_bindings):
                yield s
    # path checks for the existence of files in the local filesystem and yields a hit if it does
    # <path match="{template}" [var="{name}"]/>
    # it is also an implicit anonymous block.
    # if template expands to a nonexistent filename it will be attempted as a glob, which will then
    # produce solutions binding to the named var for each glob match
    elif expr.tag=='path':
        try:
            match_expr = coalesce(expr.get('match'),'')
        except UnboundVariable, uv:
            logging.warn('path: unbound variable %s' % uv)
            return # pass
        if os.path.exists(match_expr) and os.path.isfile(match_expr):
            inner_bindings = {parse_var_arg(expr): match_expr}
            # hit; recur on inner block
            for s in inner_block(expr,inner_bindings):
                yield s
        else:
            def S():
                for glob_hit in sorted(list(iglob(match_expr))):
                    yield {parse_var_arg(expr): glob_hit}
            for s in inner_block(expr,solution_generator=S()):
                yield s
    # read produces each line of a specified source as solution bound to the given var.
    # if no var is specified each line is bound to a variable named '_'
    # <lines [file="{filename}|url="{url}"] [var="{name}"]/>
    # and is also an implicit block. if no file is specified stdin is read
    elif expr.tag=='lines':
        var_name = parse_var_arg(expr)
        url, file_path = parse_source_arg(expr)
        if url is not None:
            iterable = urlopen(url)
        else:
            iterable = fileinput.input(file_path)
        def S():
            for raw_line in iterable:
                yield {var_name: raw_line.rstrip()}
        for s in inner_block(expr,solution_generator=S()):
            yield s
    # csv reads CSV data from a source to bind selected variables.
    # <csv [file="{filename}|url="{url}"] [vars="{name1} {name2}"]/>
    # if no vars are specified the CSV data must have a header row
    # and those headers will be used as variable names
    elif expr.tag=='csv':
        vars = parse_vars_arg(expr)
        url, file_path = parse_source_arg(expr)
        stream = open_source_arg(url, file_path)
        reader = csv.DictReader(stream,vars)
        def S():
            for s in reader:
                yield flatten(s,vars)
        for ss in inner_block(expr,solution_generator=S()):
            yield ss
    # <json var={name} [select={query}] [file={pathname}|url={url}|from={name}]/>
    elif expr.tag=='json':
        url, file_path = parse_source_arg(expr)
        select = expr.get('select')
        from_arg = expr.get('from')
        var = expr.get('var') # important: don't use parse_var_arg so not to default to _
        if from_arg is not None:
            parsed = bindings[from_arg]
        else:
            parsed = json.load(open_source_arg(url, file_path))
        if select is None and var is not None:
            for ss in inner_block(expr,{var:parsed}):
                yield ss
        else:
            def S():
                for result in jsonquery(parsed, select):
                    if var is None:
                        yield result
                    else:
                        yield {var: result}
            for ss in inner_block(expr,solution_generator=S()):
                yield ss
    # all other tags are no-ops, but because this a block will recur
    # to subsequent expressions
    # FIXME change this behavior
    else:
        for s in rest(expr):
            yield s

# invoke a named rule
def invoke(name,bindings={},global_namespace={}):
    try:
        expr = global_namespace[name]
    except KeyError:
        logging.warn('invoke: no such rule %s' % name)
        return
    if expr.tag == 'rule':
        # enforce required variables
        uses = parse_vars_arg(expr,'uses')
        if uses is not None:
            for u in uses:
                if u not in bindings:
                    logging.warn('invoke: missing variable in uses: %s' % u)
                    return
        # generate block-level solutions (pre-filter)
        raw_block = evaluate_block(list(expr),bindings,global_namespace=global_namespace)
        # now filter the solutions with block-level modifiers
        for solution in with_block(raw_block,expr,bindings):
            yield solution
    else:
        logging.warn('invoke: %s is not a rule' % name)

def parse(*ldr_streams):
    namespace = {}
    for ldr_stream in ldr_streams:
        try:
            xml = etree.parse(ldr_stream).getroot()
        except etree.XMLSyntaxError:
            raise
        except:
            xml = etree.fromstring(ldr_stream)
        # first, strip comments
        for c in xml.xpath('//comment()'):
            p = c.getparent()
            p.remove(c)
        namespace.update(find_names(xml).items())
    return namespace

class Resolver(object):
    def __init__(self,*files):
        self.namespace = parse(*files)
        self._add_positional_functions()
    def invoke(self,name,**bindings):
        for s in invoke(name,bindings,self.namespace):
            yield s
    def as_function(self,name):
        def _fn(**bindings):
            return self.invoke(name,**bindings)
        return _fn
    def as_positional_function(self,name):
        e = self.namespace[name]
        uses = coalesce(parse_vars_arg(e,'uses'),[]) # FIXME encapsulation violation
        def _fn(*args,**bindings):
            kw = dict(zip(uses,args))
            kw.update(bindings)
            return self.invoke(name,**kw)
        return _fn
    def _add_positional_functions(self):
        """decorate this object so that if you call R.foo.bar.baz
        with positional arguments it will invoke 'foo.bar.baz' eg
        foo.bar.baz that is using x and y, that you can invoke it
        r.foo.bar.baz(x,y)"""
        obj = self
        for name in sorted(self.namespace,key=lambda k: len(k)):
            level = obj
            parts = re.split(r'\.',name)
            for part in parts[:-1]:
                if not getattr(level, part, None):
                    setattr(level, part, lambda _: None)
                level = getattr(level, part)
            setattr(level, parts[-1], self.as_positional_function(name))

# utilities for finding resolvers on the Python path

@memoize()
def locate_resolver(relative_path):
    return search_path(relative_path)
    
def get_resolver(relative_path):
    return Resolver(locate_resolver(relative_path))

if __name__=='__main__':
    """usage example
    python oii/ldr.py foo.xml:bar.xml some.resolver.name var1=val1 var2=val2 ...
    """
    path, name = sys.argv[1:3]
    xml_files = re.split(':',path)
    bindings = dict(re.split('=',kw) for kw in sys.argv[3:])

    resolver = Resolver(*xml_files)
    n = 0
    for result in resolver.invoke(name,**bindings):
        n += 1
        pprint(result,'Solution %d' % n)
