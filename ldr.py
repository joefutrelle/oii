import sys
import os
from StringIO import StringIO
from lxml import etree
import re
from glob import iglob

import traceback

from oii.scope import Scope
from oii.utils import coalesce, asciitable

# pretty-print bindings
def pprint(bindings):
    if len(bindings) == 0:
        print '{}'
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
    print '{'
    for var in sorted(bindings):
        print '%s%s: "%s"' % (' ' * (width-len(var)),var,bindings[var])
    print '}'

# foo.bar corresponds to an XPath of /rule[@name='foo']/namespace[@name='bar']
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

LDR_INTERP_PATTERN = re.compile(r'([^\$]*)(\$\{([a-zA-Z0-9_]+)\})')
LDR_WS_SEP_REGEX = r'\s+'
LDR_WS_SEP_PATTERN = re.compile(LDR_WS_SEP_REGEX)

def flatten(dictlike, key_names=None):
    if key_names is None:
        return dict(dictlike.items())
    return dict((k,dictlike[k]) for k in key_names if k in dictlike)

# substitute patterns like ${varname} for their values given
# scope = values for the names (dict-like)
# e.g., interpolate('${x}_${blaz}',{'x':'7','bork':'z','blaz':'quux'}) -> '7_quux'
def interpolate(template,scope):
    s = StringIO()
    end = 0
    for m in re.finditer(LDR_INTERP_PATTERN,template):
        end = m.end()
        (plain, expr, key) = m.groups()
        s.write(plain)
        try:
            s.write(scope[key])
        except KeyError:
            s.write(expr)
    s.write(template[end:])
    return s.getvalue()

## interpolate a template using Jinja2
#import jinja2
#def interpolate(template,scope):
#    return jinja2.Environment().from_string(template).render(**scope.flatten())

# utility to parse "vars" argument
def parse_vars_arg(expr,attr='vars'):
    var_name_list = expr.get(attr)
    if var_name_list:
        return re.split(LDR_WS_SEP_PATTERN,var_name_list)
    return None

# filter out distinct solutions. if vars is specified,
# retain only those vars prior to testing for uniqueness.
# if expr is specified parse the 'distinct' argument from it
# to get the var list.
# if neither is specified, allow all solutions
def distinct(solution_generator,expr=None,vars=None):
    if expr is not None:
        vars = parse_vars_arg(expr,'distinct')
    if vars is not None:
        distinct_solutions = set()
        for raw_solution in solution_generator:
            solution = flatten(raw_solution,vars)
            f_solution = frozenset(solution.items())
            if f_solution not in distinct_solutions:
                distinct_solutions.add(f_solution)
                yield solution
    else:
        for s in solution_generator:
            yield s

# evaluate a block of expressions using recursive descent to generate and filter
# solutions a la Prolog
def evaluate_block(exprs,bindings=Scope(),global_namespace={}):
    # utility to parse arguments to match and split
    def parse_match_args(expr,bindings,default_pattern='.*'):
        pattern = coalesce(expr.get('pattern'),default_pattern)
        if expr.get('value'):
            value = expr.get('value')
        elif expr.get('var'):
            value = bindings[expr.get('var')]
        return interpolate(pattern,bindings), interpolate(value,bindings)
    # utility block evaluation function using this expression's bindings and global namespace
    def local_block(exprs,inner_bindings={}):
        return evaluate_block(exprs,bindings.enclose(**inner_bindings),global_namespace)
    # utility recurrence expression establishes an inner scope and evaluates
    # the remaining expressions (which will yield solutions to the head expression)
    # usage: for s in rest(exprs,bindings): yield s
    def rest(inner_bindings={}):
        return local_block(exprs[1:],inner_bindings)
    # utility recurrence expression for unnamed block
    def inner_block(expr,inner_bindings={}):
        for s in distinct(local_block(list(expr),inner_bindings),expr):
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
    # or optionally, a subset of them
    # <hit vars="{name1} {name2}"/>
    # then recurs. it's the only way to generate a hit and recur;
    # otherwise one can just fall through.
    # The retain expression is just like this, except that it doesn't
    # generate a hit but rather falls through after reducing the set
    # of variables in the solution.
    elif expr.tag in ('hit','retain'):
        var_names = parse_vars_arg(expr)
        if var_names:
            s = flatten(bindings, var_names)
        else:
            s = flatten(bindings)
        if expr.tag=='hit':
            yield s
            for ss in rest(s):
                yield ss
        elif expr.tag=='retain':
            for ss in evaluate_block(exprs[1:],s,global_namespace):
                yield ss
    # Invoke means descend, once, into a named rule, evaluating it as a block,
    # with the current bindings in scope, and recur for each of its solutions.
    # options include filtering the input and output variables, as well as
    # aliasing the output variables
    # <invoke rule="{name}" [using="{var1} {var2}"] [toget="{var1} {var2}" [as="{alias1} {alias2}"]]"/>
    elif expr.tag=='invoke':
        rule_name = expr.get('rule')
        using = parse_vars_arg(expr,'using')
        toget = parse_vars_arg(expr,'toget')
        aliases = parse_vars_arg(expr,'as')
        for s in distinct(invoke(rule_name,Scope(flatten(bindings,using)),global_namespace),expr):
            if toget is not None and aliases is not None:
                s = dict((a,s[k]) for k,a in zip(toget,aliases))
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
        var_name = expr.get('name')
        sub_val_exprs = expr.findall('val')
        if len(sub_val_exprs) == 0:
            var_val = interpolate(expr.text,bindings)
            for s in rest({var_name:var_val}):
                yield s
        else:
            for sub_val_expr in sub_val_exprs:
                var_val = interpolate(sub_val_expr.text,bindings)
                for s in rest({var_name:var_val}):
                    yield s
    # The vars expression is the plural of var, for multiple assignment
    # with any regex as a delimiter between variable values.
    # <vars names="{name1} {name2} [delim="{delim}"]>{value1}{delim}{value2}</vars>
    # or
    # <vars names="{name1} {name2} [delim="{delim}"]>
    #   <vals>{value1}{delim}{value2}</vals>
    #   <vals>{value1}{delim}{value2}</vals>
    # </vars>
    elif expr.tag=='vars':
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
            for s in local_block([sub_expr]): # treat each one as a block
                for ss in rest(s):  # and recur for each of its solutions
                    yield ss
                    if expr.tag=='first': # if all we want is the first
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
            return
        # if we fell through, there were no solutions
        for s in rest():
            yield s
    # log interpolates its text and prints it. useful for debugging
    # <log>{template}</log>
    elif expr.tag=='log':
        print interpolate(expr.text,bindings)
        for s in rest():
            yield s
    # match generates solutions for every regex match
    # <match pattern="{regex}" [value="{template}"|var="{variable to match}"] [groups="{name1} {name2}"]/>
    # if "value" is specified, the template is interpolated and then matched against,
    # if "var" is specified, the variable's value is looked up and then matched.
    # var="foo" is equivalent to value="${foo}"
    # if pattern is not specified the default pattern is ".*"
    # match also acts as an implicit, unnamed block so
    # <match ...>
    #   {expr1}
    #   {expr2}
    # </match>
    # is equivalent to
    # <all>
    #   <match .../>
    #   {expr1}
    #   {expr2}
    # </all>
    elif expr.tag=='match':
        pattern, value = parse_match_args(expr,bindings,'.*')
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
    # split iterates over the result of splitting a value by a regex, assigning it repeatedly
    # to the variable specified by group. like match it recurs and is also an implicit block
    # <split [var="{var}"|value="{template}"] [pattern="{pattern}"] [group="{name}|vars="{name1} {name}"]/>
    # if pattern is not specified the default pattern is "  *"
    # alternatively one can use split to do multiple assignment, as in this example
    # <split value="foo bar baz" vars="a b c"/>
    # which will set a=foo, b=bar, c=baz
    elif expr.tag=='split':
        pattern, value = parse_match_args(expr,bindings,default_pattern=LDR_WS_SEP_REGEX)
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
        match_expr = interpolate(template,bindings)
        if os.path.exists(match_expr) and os.path.isfile(match_expr):
            if expr.get('var'):
                inner_bindings = {expr.get('var'): match_expr}
            else:
                inner_bindings = {}
            # hit; recur on inner block
            for s in inner_block(expr,inner_bindings):
                yield s
        else:
            for glob_hit in iglob(match_expr):
                inner_bindings = {expr.get('var'): glob_hit}
                for s in inner_block(expr,inner_bindings):
                    yield s
    # all other tags are no-ops, but because this a block will recur
    # to subsequent expressions
    else:
        for s in rest():
            yield s

def invoke(name,bindings=Scope(),global_namespace={}):
    expr = global_namespace[name]
    if expr.tag == 'rule':
        for solution in distinct(evaluate_block(list(expr),bindings,global_namespace=global_namespace),expr):
            yield solution

def parse(*ldr_streams):
    namespace = {}
    for ldr_stream in ldr_streams:
        try:
            xml = etree.parse(ldr_stream).getroot()
        except:
            xml = etree.fromstring(ldr_stream)
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
    for line in asciitable(list(resolver.resolve(name,**bindings))):
        print line

