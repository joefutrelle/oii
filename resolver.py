#!/usr/bin/python
from lxml import etree
from collections import namedtuple
import re
from glob import iglob
from os import path
import sys
import readline
import cmd
import traceback

# "little language" pattern

Match = namedtuple('Match', ['var','regex', 'expressions', 'groups'])
MatchImport = namedtuple('MatchImport', ['resolver'])
Var = namedtuple('Var', ['name','values', 'hit'])
Path = namedtuple('Path', ['var', 'match', 'expressions'])
Any = namedtuple('Any', ['expressions'])
All = namedtuple('All', ['expressions', 'hit'])
Hit  = namedtuple('Hit', ['value', 'stop'])
Import = namedtuple('Import', ['name'])
Log = namedtuple('Log', ['message'])

# implicit terminal Hit on Match with subexpressions
END = [Hit('',stop=False)]

TRUE=['yes', 'true', 'True', 'T', 't', 'Y', 'y', 'Yes']

# convert XML format into named tuple representation.
# a resolver is a sequence of expressions, each of which is
# either a Match, Var, Path, Any, or Hit expression.
# for details on the syntax see the resolve function
def sub_parse(node):
    for child in node:
        if child.tag == 'match' and child.get('resolver'): # matchimport
            yield MatchImport(child.get('resolver'))
        elif child.tag == 'match':
            var = child.get('var')
            pattern = child.get('pattern')
            value = child.get('value')
            groups = child.get('groups')
            if groups is not None:
                groups = re.compile(r'\s+').split(groups)
            if pattern is not None:
                yield Match(var, regex=pattern, expressions=list(sub_parse(child)), groups=groups)
            elif value is not None:
               yield Match(var, regex='^%s$' % value, expressions=list(sub_parse(child)), groups=groups)
            else:
                yield Match(var, regex=child.text, expressions=None, groups=groups)
        elif child.tag == 'var' or (child.tag == 'hit' and child.get('name') is not None):
            hit = False
            if child.tag == 'hit':
                hit = True
            values = [gc.text for gc in child if gc.tag == 'value'];
            if not values:
                values = [child.text]
            yield Var(name=child.get('name'), values=values, hit=hit)
        elif child.tag == 'path':
            yield Path(var=child.get('var'), match=child.get('match'), expressions=list(sub_parse(child)))
        elif child.tag == 'any':
            yield Any(expressions=list(sub_parse(child)))
        elif child.tag == 'all':
            hit = child.get('hit')
            if hit is not None:
                yield All(expressions=list(sub_parse(child)), hit=hit)
            else:
                yield All(expressions=list(sub_parse(child)), hit=None)
        elif child.tag == 'import':
            yield Import(name=child.get('name'))
        elif child.tag == 'hit':
            stop = child.get('stop')
            if stop is not None:
                yield Hit(value=child.text, stop=stop in TRUE)
            elif child.text is None:
                yield Hit('', stop=False)
            else:
                yield Hit(value=child.text, stop=False)
        elif child.tag == 'log':
            yield Log(message=child.text)

# parsing entry point. use parse_stream instead
def parse(pathname,resolver_name=None):
    if resolver_name is None:
        r = etree.parse(pathname).getroot()
    else:
        for child in etree.parse(pathname).getroot():
            if child.tag == 'resolver' and child.get('name') == resolver_name:
                r = child
                break
    return list(sub_parse(r))

class Solution(object):
    """Internal use only"""
    def __init__(self,value,bindings):
        self.value = value
        self.bindings = bindings
        self.bindings['value'] = value
        for k,v in bindings.items():
            setattr(self,k,v)
    def __repr__(self):
        return '<Solution: %s %s>' % (self.value, self.bindings)

RESERVED_NAMES = ['value', 'bindings']

# substitute patterns like ${varname} for their values given
# bindings = a dict of varname->value
# e.g., substitute('${x}_${blaz}',{'x':'7','bork':'z','blaz':'quux'}) -> '7_quux'
def substitute(template,bindings):
    result = template
    for key,value in bindings.items():
        if value is not None:
            result = re.sub('\$\{'+key+'\}',value,result)
    return result

# recursive resolution engine that handles one expression
# resolver - parsed resolution script
# bindings - var name -> value mappings
# cwd - current working directory (recursively descends)
# yields hits. each hit is a tuple consiting of
# 1. the value (i.e., the pathname that matched, or the contents of a <hit> tag
# 2. the bindings of all vars at the time the solution was yielding
# note that during recursive descent bindings act like a stack
def resolve(resolver,bindings,cwd='/',namespace={}):
    if not resolver: # no more expressions left?
        return
    expr = resolver[0]
    #print (expr,bindings) # FIXME debug
    if isinstance(expr,Any):
        # "any" means to accept any matching subexpression instead of terminating
        # if the first one doesn't match. For example
        # <any>
        #   <match var="pid">.*((D\d{4}\d{4})T\d{6}_\IFCB\d+)</match>
        #   <match var="pid">.*((IFCB\d+_\d{4}_\d{3})_\d{6})</match>
        # </any>
        # will try both pid syntaxes and any match will bind the groups and
        # evaluate the rest of the resolver following the </any> tag.
        # if there are no matches, execution will not proceed to the rest of the
        # resolver that follows the <any> tag.
        for ex in expr.expressions:
            for solution in resolve([ex] + resolver[1:], bindings, cwd, namespace):
                yield solution
    elif isinstance(expr,Log):
        print substitute(expr.message, bindings)
        for solution in resolve(resolver[1:], bindings, cwd, namespace):
            yield solution
    elif isinstance(expr,All):
        # "all" means that all subexpressions mus match; it is the explicit form of the implicit
        # behavior of an entire resolver. If any subexpression does not produce variable bindings or a solution,
        # then "all" produces no solutions for its parents. an optional "hit" attribute, if present, means that
        # the "all" will always produce a hit after all subexpressions match; the contents of the "hit" attribute
        # are a template that will be produced as the solution.
        # this can be used in conjunction with any to iterate over groups of variable bindings:
        # <any>
        #   <all>
        #     <var name="a">A</var>
        #     <var name="b">B</var>
        #   </all>
        #   <all>
        #     <var name="a">a</var>
        #     <var name="b">b</var>
        #   </all>
        # </any>
        # <hit>${a}${b}</hit>
        # yields "AB" and "ab"
        expr_hit = expr.expressions
        if expr.hit is not None:
            expr_hit = expr_hit + [Hit(expr.hit, stop=False)]
        for solution in resolve(expr_hit + resolver[1:], bindings, cwd, namespace):
            yield solution
    elif isinstance(expr,Hit):
        # "hit" immediately yields a solution, then continues, unless "stop" is true.
        # so <hit>foo</hit> yields a hit on 'foo'
        yield Solution(substitute(expr.value,bindings), bindings)
        if not expr.stop:
            for solution in resolve(resolver[1:],bindings,cwd,namespace):
                yield solution
    elif isinstance(expr,Match):
        # "match" means test a variable against a regex, and (optionally) match groups
        # group n will be bound to ${n+1}, so for instance if variable
        # "foo" is "yes,no,123" then
        # <match var="foo">([a-z]+),([a-z]+),(\d+)</match>
        # will add the following bindings
        # ${1} -> "yes"
        # ${2} -> "no"
        # ${3} -> "123"
        # if there is no match, execution stops.
        # optionally, "groups" can be provided to assign groups to variables without
        # needing <var> statements, as such:
        # <match var="foo" groups="w1 w2 num">([a-z]+),([a-z]+),(\d+)</match>
        # will add the following bindings:
        # ${w1} -> "yes"
        # ${w2} -> "no"
        # ${num} -> "123"
        # note that if a group doesn't match any existing value will be retained rather than
        # being set to None, and that allows for defaults. if you want the matched group itself
        # in that case, you can use numbered bindings;
        # numbered bindings will also be added for each group. Importantly,
        # this variant also means that any non-matching subexpression will result in a binding
        # of None rather than an unmodified variable reference such as "${3}" and so it's
        # a good way to test for the presence of a group.
        # A syntax variant allows sub-expressions to be evaluated conditionally
        # depending on whether or not there is a match. in this case a match
        # causes execution to descend into the subexpressions and terminate;
        # no match causes execution to continue on the remainder of the resolver.
        # to avoid termination use <any>
        # <match var="foo" pattern="([a-z]+),([a-z]+),(\d+)">
        #     <var name="bar">${1}_${2}</var>
        #     ...
        # </match>
        # The "value" attribute is shorthand for wrapping the "pattern" attribute in ^$
        value = bindings[expr.var] # look up the variable's value
        m = None
        if value is not None: # if the variable has no value, then don't attempt a regex match
            m = re.match(substitute(expr.regex,bindings), value) # perform a regex match
        if m is not None: # is there a match?
            groups = m.groups() # get the matching groups
            local_bindings = bindings.copy() # create a new bindings stack frame
            for index,group in zip(range(len(groups)), groups): # bind numbered variables to groups
                local_bindings[str(index+1)] = group
            if expr.groups is not None: # bind names in "groups" attribute to groups
                for var,group in zip(expr.groups, groups):
                    if group is not None or var not in local_bindings:
                        local_bindings[var] = group
            if expr.expressions is not None: # there are subexpressions, so descend as a result of the match
                for solution in resolve(expr.expressions,local_bindings,cwd,namespace):
                    yield solution
            else: # matched, and no subexpressions, so continue with the rest of the resolver
                for solution in resolve(resolver[1:],local_bindings,cwd,namespace):
                    yield solution
        elif expr.expressions is not None:
            # no match, so skip subexpressions and keep going
            for solution in resolve(resolver[1:],bindings,cwd,namespace):
                yield solution
    elif isinstance(expr,Var):
        # "var" means bind a variable from a template that may optionally
        # include variable references. So if ${3} is bound to "foo",
        # <var name="fb">${3}bar</var>
        # will add the binding
        # ${fb} -> "foobar"
        # if the var has multiple "value" sub-elements, those will be
        # bound one at a time, and the rest of the resolver will be evaluated
        # for each binding. So for example
        # <var name="fb">
        #   <value>${3}bar</value>
        #   <value>${3} fighters</value>
        # </var>
        # will evaluate the rest of the resolver, first with ${fb} bound to "foobar",
        # and then with ${fb} bound to "foo fighters"
        # Note that this is simply a convenience as it is equivalent to
        # <any>
        #   <var name="fb">${3}bar</var>
        #   <var name="fb">${3} fighters</var>
        # </any>
        name = expr.name
        if name in RESERVED_NAMES:
            raise KeyError('"%s" is not permitted as a variable name in resolvers' % name)
        for template in expr.values:
            local_bindings = bindings.copy()
            local_bindings[name] = substitute(template,bindings)
            if expr.hit: # hit now?
                yield Solution(local_bindings[name], local_bindings)
            # and continue
            for solution in resolve(resolver[1:],local_bindings,cwd,namespace):
                yield solution
    # A variant of match allows to use an imported resolver to generate hits.
    elif isinstance(expr,MatchImport):
        imported = namespace[expr.resolver] # import the named resolver
        for solution in resolve(imported,bindings,cwd,namespace):
            yield solution
            local_bindings = solution.bindings.copy()
            # and do the rest of this resolver
            for subs in resolve(resolver[1:],local_bindings,cwd,namespace):
                yield subs
    elif isinstance(expr,Import):
        # <import> allows for descending into a named resolver outside
        # of the importing resolver. The imported resolver is executed
        # with current bindings and every hit it generates adds
        # additional local bindings, and then the rest of the
        # importing resolver is executed with those bindings. If the
        # intention is to instead allow the imported resolver to
        # generate hits on behalf of the importing resolver, use
        # <match resolver="..."> instead (i.e., MatchImport)
        imported = namespace[expr.name] # import the named resolver
        for solution in resolve(imported,bindings,cwd,namespace):
            # for each of its solutions, use its bindings
            local_bindings = solution.bindings.copy()
            # and do the rest of this resolver
            for subs in resolve(resolver[1:],local_bindings,cwd,namespace):
                yield subs
    elif isinstance(expr,Path):
        # "path" is where the filesystem is searched for a matching file.
        # there are two variants of this expression. one looks for a file
        # that matches the given name. if one is found, the resolver yields
        # its pathname. for example if ${f} is bound to "blah.txt",
        # <path match="/some/directory/${f}"/>
        # will yield a hit if /some/directory/blah.txt exists and is a file
        # (i.e., not a directory).
        # the other variant is used for listing directories, and so the
        # path can contain globbing expressions like "/xyz/*/blah"
        # in that variant, all matching files and/or directories are successively
        # bound to the given variable, and the inner resolver is evaluated with
        # each of those files/directories as the "current working directory" (for
        # futher globbing).
        # (if it's not a directory, that's OK, it just means further descent is
        # not possible).
        # for example, if ${pid} is "apache2",
        # <path var="service" match="/etc/rc*.d/*">
        #   <match var="service">/etc/rc\d.d/([A-Z]\d+)${pid}</match>
        #   <path match="${service}"/>
        # </path>
        # will resolve to paths like /etc/rc0.d/K02apache2, but not paths like
        # /etc/rc0.d/README or /etc/rcS.d/K99apache2
        var = expr.var
        candidate = path.join(cwd, substitute(expr.match,bindings))
        if var is None and path.exists(candidate) and path.isfile(candidate):
            yield Solution(candidate,bindings)
        else:
            for hit in iglob(candidate):
                local_bindings = bindings.copy()
                if var is not None:
                    local_bindings[var] = hit
                # done, now evaluate the inner resolver if any
                for solution in resolve(expr.expressions, local_bindings, hit, namespace):
                    yield solution

class Resolver(object):
    """Class handling resolution"""
    def __init__(self,expressions,name,namespace={}):
        """Internal use only. Use parse_stream as a resolver factory"""
        self.expressions = expressions
        self.name = name
        self.namespace = namespace
    def resolve_all(self,**bindings):
        """Iterate over all solutions, and include bindings with each solution"""
        for solution in resolve(self.expressions, bindings, namespace=self.namespace):
            yield solution
    def resolve(self,**bindings):
        """Return the first hit, and do not include bindings with the solution.
        Returns None if there are no hits"""
        for solution in self.resolve_all(**bindings):
            return solution

def parse_node(node):
    """Parse an etree XML node and return a dictionary of all named
    resolvers immediately below it"""
    namespace = {}
    for child in node:
        if child.tag == 'resolver':
            name = child.get('name')
            namespace[name] = list(sub_parse(child))
    result = {}
    for n,e in namespace.items():
        result[n] = Resolver(e,n,namespace)
    return result

def parse_stream(stream):
    """Parse an XML document and return a dictionary of all named
    resolvers immediately below the root node"""
    return parse_node(etree.parse(stream).getroot())

# example configuration
# this takes pids like
#   UNQ.20110621.153252431.1423
# pathnames like
#   /mnt/nmfs-2/webdata/HabCam/data/Cruises/HS_20110621/Images/Full/20110621_1530/UNQ.20110621.153252431.1423.jpg
#
# <resolver name="habcam-jpg">
#     <match var="pid">([A-Z]+\.((\d{4})\d{4})\.(\d{3}).*)</match>
#     <var name="filename">${1}.jpg</var>
#     <var name="day">${2}</var>
#     <var name="year">${3}</var>
#     <var name="img_dir">${day}_${4}0</var>
#     <var name="root">/mnt/nmfs-2/webdata/HabCam/data/Cruises</var>
#     <path var="cruise_dir" match="${root}/*">
#         <match var="cruise_dir">.*/[A-Z]{2}_\d+</match>
#         <path match="Images/Full/${img_dir}/${filename}"/>
#     </path>
# </resolver>
#
# note that the computation of the name of the ten minute directory in
# this case can be done as a text substitution.  if arithmetic is
# required, this class doesn't currently support any such operations.

def print_bindings(bindings):
    for var in bindings.keys():
        try:
            int(var)
            del bindings[var]
        except ValueError:
            pass
    # colon-align
    width = max([len(var) for var in bindings.keys()])
    print '{'
    for var in sorted(bindings.keys()):
        print '%s%s: "%s"' % (' ' * (width-len(var)),var,bindings[var])
    print '}'

def interactive_shell(resolvers):
    bindings = {}
    class Shell(cmd.Cmd):
        def do_list(self,args):
            for name in sorted(resolvers.keys()):
                print '- %s' % name
        def do_clear(self,args):
            bindings = {}
        def do_bind(self,args):
            for kv in re.split(' +',args):
                (k,v) = re.split(r'=',kv)
                bindings[k] = v
        def do_show(self,args):
            print_bindings(bindings)
        def do_run(self,resolver_name):
            try:
                for solution in resolvers[resolver_name].resolve_all(**bindings):
                    print 'Solution: "%s"' % solution.value
                    print_bindings(solution.bindings)
            except:
                traceback.print_exc(file=sys.stdout)
    Shell().cmdloop('Found %d resolver(s) in %s:' % (len(resolvers), resolver_file))

# FIXME split CLI into different module

if __name__=='__main__':
    """Usage:
    python resolver.py {resolver file} {resolver name} {key0=value0 key1=value1 ... keyN=valueN}"""
    args = sys.argv
    resolver_file = args[1]
    resolvers = parse_stream(resolver_file)
    if len(args)==2:
        interactive_shell(resolvers)
    else:
        resolver_name = args[2]
        bindings = {}
        for kv in args[3:]:
            (k,v) = re.split(r'=',kv)
            bindings[k] = v
        for solution in resolvers[resolver_name].resolve_all(**bindings):
            bindings = solution.bindings
            for var in bindings.keys():
                try:
                    int(var)
                    del bindings[var]
                except ValueError:
                    pass
            # colon-align
            width = max([len(var) for var in bindings.keys()])
            print 'Solution: "%s" {' % solution.value
            for var in sorted(bindings.keys()):
                print '%s%s: "%s"' % (' ' * (width-len(var)),var,bindings[var])
            print '}'

            
