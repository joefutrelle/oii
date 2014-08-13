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

from oii.scope import Scope
from oii.utils import coalesce, asciitable
from oii.jsonquery import jsonquery

class UnboundVariable(Exception):
    pass

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
    pattern = re.sub(r'9','[0-9]',pattern)
    pattern = re.sub(r's+','(?P<millisecond>[0-9]+)',pattern)
    pattern = re.sub(r'yyyy','(?P<year>[0-9]{4})',pattern)
    pattern = re.sub(r'mm','(?P<month>0?[1-9]|11|12)',pattern)
    pattern = re.sub(r'dd','(?P<day>0?1|[1-2][0-9]|3[0-1])',pattern)
    pattern = re.sub(r'YYY','(?P<yearday>[0-3][0-9][0-9])',pattern)
    pattern = re.sub(r'HH','(?P<hour>0[1-9]|1[0-9]|2[0-3])',pattern)
    pattern = re.sub(r'MM','(?P<minute>[0-5][0-9])',pattern)
    pattern = re.sub(r'SS','(?P<second>[0-5][0-9])',pattern)
    return pattern

def flatten(dictlike, include=None, exclude=None):
    result = dict(dictlike.items())
    if include is not None:
        result = dict((k,result[k]) for k in result if k in include)
    if exclude is not None:
        result = dict((k,result[k]) for k in result if k not in exclude)
    return result

# substitute patterns like ${varname} for their values given
# scope = values for the names (dict-like)
# e.g., interpolate('${x}_${blaz}',{'x':'7','bork':'z','blaz':'quux'}) -> '7_quux'
#import jinja2
def interpolate(template,scope,fail_fast=True):
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

def open_source_arg(url=None, file_arg=None, bindings={}):
    if url is not None:
        return urlopen(interpolate(url,bindings))
    elif file_arg is not None:
        return open(interpolate(file_arg,bindings))
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
        s = Scope(flatten(raw_solution,include,exclude))
        yield s

# apply block-level modifications such as distinct, rename, include/exclude, count, and nth
def with_block(S,expr,bindings={}):
    bindings = flatten(bindings)
    # include/exclude
    include = parse_vars_arg(expr,'include')
    exclude = parse_vars_arg(expr,'exclude')
    if include is not None or exclude is not None:
        S = with_inc_exc(S,include,exclude)
    # distinct
    distinct = parse_vars_arg(expr,'distinct')
    if distinct is not None:
        S = with_distinct(S,distinct)
    # count
    count = expr.get('count')
    nth = expr.get('nth')
    if nth is not None:
        nth = int(interpolate(nth,bindings))
    S = with_count(S,count,nth)
    # rename/as
    rename = parse_vars_arg(expr,'rename')
    rename_as = parse_vars_arg(expr,'as')
    try:
        aliases = dict((o,n) for o,n in zip(rename,rename_as))
        S = with_aliases(S,aliases)
    except TypeError:
        pass
    for s in S:
        yield s

# evaluate a block of expressions using recursive descent to generate and filter
# solutions a la Prolog
def evaluate_block(exprs,bindings=Scope(),global_namespace={}):
    # utility to parse arguments to match and split
    def parse_match_args(expr,bindings,default_pattern='.*'):
        pattern = coalesce(expr.get('pattern'),expr.get('timestamp'),default_pattern)
        if expr.get('value'):
            value = expr.get('value')
        else:
            var_arg = parse_var_arg(expr)
            try:
                value = str(bindings[var_arg])
            except KeyError: # the caller is attempting to match an unbound variable
                raise UnboundVariable(var_arg)
        i_pattern = interpolate(pattern,bindings)
        if expr.get('timestamp'):
            i_pattern = timestamp2regex(i_pattern)
        i_value = interpolate(value,bindings)
        return i_pattern, i_value
    # utility block evaluation function using this expression's bindings and global namespace
    def local_block(exprs,inner_bindings={}):
        return evaluate_block(exprs,bindings.enclose(inner_bindings),global_namespace)
    # utility recurrence expression establishes an inner scope and evaluates
    # the remaining expressions (which will yield solutions to the head expression)
    # usage: for s in rest(exprs,bindings): yield s
    def rest(inner_bindings={}):
        return local_block(exprs[1:],inner_bindings)
    # utility recurrence expression for unnamed block
    def inner_block(expr,inner_bindings={}):
        for s in with_block(local_block(list(expr),inner_bindings),expr,bindings):
            for ss in rest(s):
                yield ss
    # terminal case; we have arrived at the end of the block with a solution, so yield it
    if len(exprs)==0:
        yield flatten(bindings)
        return
    # handle the first expression
    expr = exprs[0]
    # The miss expression indicates no match has been found.
    # So refuse to recur, will not yield any solutions
    if expr.tag=='miss':
        return
    # The hit expression means a match has been found.
    # So yield the current set of bindings.
    # <hit/>
    # or optionally, a subset of them defined via include
    # <hit include="{name1} {name2}"/>
    # or exclude
    # <hit exclude="{name1} {name2}"/>
    # then recurs. it's the only way to generate a hit and recur;
    # otherwise one can just fall through.
    elif expr.tag=='hit':
        include = parse_vars_arg(expr,'include')
        exclude = parse_vars_arg(expr,'exclude')
        s = Scope(flatten(bindings, include=include, exclude=exclude))
        yield s # this is where we produce a solution
        for ss in evaluate_block(exprs[1:],s,global_namespace):
            yield ss
    # include deletes all bindings except the ones mentioned.
    # <include vars="{var1} {var2}"/>
    elif expr.tag=='include':
        include = parse_vars_arg(expr)
        s = Scope(flatten(bindings, include=include))
        for ss in evaluate_block(exprs[1:],s,global_namespace):
            yield ss
    # exclude deletes the specified bindings.
    # <exclude vars="{var1} {var2}"/>
    elif expr.tag=='exclude':
        exclude = parse_vars_arg(expr)
        s = Scope(flatten(bindings, exclude=exclude))
        for ss in evaluate_block(exprs[1:],s,global_namespace):
            yield ss
    # Invoke means descend, once, into a named rule, evaluating it as a block,
    # with the current bindings in scope, and recur for each of its solutions.
    # options include filtering the input variables, including
    # all block level operations e.g., distinct and rename/as
    # <invoke rule="{name}" [using="{var1} {var2}"]/>
    elif expr.tag=='invoke':
        rule_name = expr.get('rule')
        using = parse_vars_arg(expr,'using')
        for s in with_block(invoke(rule_name,Scope(flatten(bindings,using)),global_namespace),expr,bindings):
            for ss in rest(s):
                yield ss
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
                var_val = interpolate(expr.text,bindings)
                for s in rest({var_name:var_val}):
                    yield s
            else:
                for sub_val_expr in sub_val_exprs:
                    var_val = interpolate(sub_val_expr.text,bindings,fail_fast=False)
                    for s in rest({var_name:var_val}):
                        yield s
        except UnboundVariable, uv:
            logging.warn('var: unbound variable in template "%s": %s' % (expr.text, uv))
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
                var_vals = map(lambda tmpl: interpolate(tmpl,bindings), re.split(delim,expr.text))
                for s in rest(dict(zip(var_names,var_vals))):
                    yield s
            else:
                for sub_val_expr in sub_val_exprs:
                    var_vals = map(lambda tmpl: interpolate(tmpl,bindings), re.split(delim,sub_val_expr.text))
                    for s in rest(dict(zip(var_names,var_vals))):
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
    # first is like any except it only yields the first solution and then stops
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
                for ss in rest(s):  # and recur for each of its solutions
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
        for s in rest():
            yield s
    # log interpolates its text and prints it. useful for debugging
    # <log>{template}</log>
    elif expr.tag=='log':
        print interpolate(expr.text,bindings,fail_fast=False)
        for s in rest():
            yield s
    # match generates solutions for every regex match
    # <match [pattern="{regex}"|timestamp="{date pattern}"] [value="{template}"|var="{variable to match}"] [groups="{name1} {name2}"]/>
    # if "value" is specified, the template is interpolated and then matched against,
    # if "var" is specified, the variable's value is looked up and then matched.
    # var="foo" is equivalent to value="${foo}"
    # if pattern is not specified the default pattern is ".*"
    # match also acts as an implicit, unnamed block supporting distinct
    elif expr.tag=='match':
        try:
            pattern, value = parse_match_args(expr,bindings,'.*')
        except UnboundVariable, uv:
            logging.warn('match: unbound variable %s' % uv)
            return # miss
        group_name_list, group_names = expr.get('groups'), []
        if group_name_list:
            group_names = re.split(LDR_WS_SEP_PATTERN,group_name_list)
        m = re.match(pattern, value)
        if m:
            groups = m.groups()
            inner_bindings = {}
            for index,group in zip(range(len(groups)), groups): # bind numbered variables to groups
                inner_bindings[str(index+1)] = group
            for name,group in zip(group_names, groups): # bind named variables to groups
                if group:
                    inner_bindings[name] = group
            # now invoke the (usually empty) inner unnamed block and recur
            for s in inner_block(expr,inner_bindings):
                yield s
        else:
            return # miss
    # test performs equality and inequality tests over strings and numbers
    # <test [var={var}|value={template}] [eq|gt|lt|ge|le|ne]={template}/>
    # and is also an implicit block
    elif expr.tag=='test':
        try:
            var = expr.get('var')
            tmpl = expr.get('value')
            if tmpl is not None:
                value = interpolate(tmpl,bindings)
            else:
                value = bindings[var]
        except KeyError:
            logging.warn('test: unbound variable %s' % var)
            return # miss
        except UnboundVariable, uv:
            logging.warn('test: unbound variable %s' % uv)
            return # miss
        op = coalesce(*[a for a in ['eq','gt','lt','ge','le','ne'] if expr.get(a)])
        tvt = expr.get(op)
        tv = interpolate(tvt,bindings)
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
            for val in re.split(pattern,value):
                # now invoke the (usually empty) inner unnamed block and recur
                for s in inner_block(expr,{group:val}):
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
        template = coalesce(expr.get('match'),'')
        try:
            match_expr = interpolate(template,bindings)
        except UnboundVariable, uv:
            logging.warn('path: unbound variable %s' % uv)
            return # pass
        if os.path.exists(match_expr) and os.path.isfile(match_expr):
            inner_bindings = {parse_var_arg(expr): match_expr}
            # hit; recur on inner block
            for s in inner_block(expr,inner_bindings):
                yield s
        else:
            for glob_hit in iglob(match_expr):
                inner_bindings = {parse_var_arg(expr): glob_hit}
                for s in inner_block(expr,inner_bindings):
                    yield s
    # read produces each line of a specified source as solution bound to the given var.
    # if no var is specified each line is bound to a variable named '_'
    # <lines [file="{filename}|url="{url}"] [var="{name}"]/>
    # and is also an implicit block. if no file is specified stdin is read
    elif expr.tag=='lines':
        var_name = parse_var_arg(expr)
        url, file_path = parse_source_arg(expr)
        if url is not None:
            iterable = urlopen(interpolate(url,bindings))
        else:
            iterable = fileinput.input(interpolate(file_path,bindings))
        for raw_line in iterable:
            line = raw_line.rstrip()
            for s in inner_block(expr,{var_name:line}):
                yield s
    # csv reads CSV data from a source to bind selected variables.
    # <csv [file="{filename}|url="{url}"] [vars="{name1} {name2}"]/>
    # if no vars are specified the CSV data must have a header row
    # and those headers will be used as variable names
    elif expr.tag=='csv':
        vars = parse_vars_arg(expr)
        url, file_path = parse_source_arg(expr)
        stream = open_source_arg(url, file_path, bindings)
        reader = csv.DictReader(stream,vars)
        for s in reader:
            for ss in inner_block(expr,flatten(s,vars)):
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
            parsed = json.load(open_source_arg(url, file_path, bindings))
        if select is None and var is not None:
            for ss in inner_block(expr,{var:parsed}):
                yield ss
        else:
            try:
                select = interpolate(select, bindings)
            except UnboundVariable, uv:
                logging.warn('json: unbound variable %s' % uv)
                return # miss
            for result in jsonquery(parsed, select):
                if var is not None:
                    result = {var: result}
                for ss in inner_block(expr,result):
                    yield ss
    # all other tags are no-ops, but because this a block will recur
    # to subsequent expressions
    # FIXME change this behavior
    else:
        for s in rest():
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

def resolve(namespace,name):
    for s in evaluate(name,global_namespace=namespace):
        yield s

class Resolver(object):
    def __init__(self,*files):
        self.namespace = parse(*files)
    def resolve(self,name,**bindings):
        for s in invoke(name,Scope(bindings),self.namespace):
            yield s
    
if __name__=='__main__':
    """usage example
    python oii/ldr.py foo.xml:bar.xml some.resolver.name var1=val1 var2=val2 ...
    """
    path, name = sys.argv[1:3]
    xml_files = re.split(':',path)
    bindings = dict(re.split('=',kw) for kw in sys.argv[3:])

    resolver = Resolver(*xml_files)
    n = 0
    for result in resolver.resolve(name,**bindings):
        n += 1
        pprint(result,'Solution %d' % n)
