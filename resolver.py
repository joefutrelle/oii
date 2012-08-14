#!/usr/bin/python
from lxml import etree
from collections import namedtuple
import re
from glob import iglob
from os import path

# "little language" pattern

Match = namedtuple('Match', ['var','regex', 'expressions', 'groups'])
Var = namedtuple('Var', ['name','values'])
Path = namedtuple('Path', ['var', 'match', 'expressions'])
Any = namedtuple('Any', ['expressions'])
Hit  = namedtuple('Hit', ['value', 'stop'])
Import = namedtuple('Import', ['name'])

# convert XML format into named tuple representation.
# a resolver is a sequence of expressions, each of which is
# either a Match, Var, Path, Any, or Hit expression.
# for details on the syntax see the resolve function
def sub_parse(node):
    for child in node:
        if child.tag == 'match':
            var = child.get('var')
            pattern = child.get('pattern')
            groups = child.get('groups')
            if groups is not None:
                groups = re.compile(r'\s+').split(groups)
            if pattern is not None:
                yield Match(var, regex=pattern, expressions=list(sub_parse(child)), groups=groups)
            else:
                yield Match(var, regex=child.text, expressions=None, groups=groups)
        elif child.tag == 'var':
            values = [gc.text for gc in child if gc.tag == 'value'];
            if not values:
                values = [child.text]
            yield Var(name=child.get('name'), values=values)
        elif child.tag == 'path':
            yield Path(var=child.get('var'), match=child.get('match'), expressions=list(sub_parse(child)))
        elif child.tag == 'any':
            yield Any(expressions=list(sub_parse(child)))
        elif child.tag == 'import':
            yield Import(name=child.get('name'))
        elif child.tag == 'hit':
            stop = child.get('stop')
            if stop is not None:
                yield Hit(value=child.text, stop=stop in ['yes', 'true', 'True', 'T', 't', 'Y', 'y', 'Yes'])
            elif child.text is None:
                yield Hit('', stop=False)
            else:
                yield Hit(value=child.text, stop=False)

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
    expr = resolver[0] # work on the first one
    #print (expr,bindings)
    if isinstance(expr,Any):
        # "any" means to accept any matching subexpression instead of terminating
        # if the first one doesn't match. For example
        # <any>
        #   <match var="pid">.*((D\d{4}\d{4})T\d{6}_\IFCB\d+)</match>
        #   <match var="pid">.*((IFCB\d+_\d{4}_\d{3})_\d{6})</match>
        # </any>
        # will try both pid syntaxes and any match will bind the groups and
        # evaluate the rest of the resolver following the </any> tag.
        for ex in expr.expressions:
            for solution in resolve([ex] + resolver[1:], bindings, cwd, namespace):
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
        # numbered bindings will also be added for each group in this case. Importantly,
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
            # done, now do the rest of the resolver
            for solution in resolve(resolver[1:],local_bindings,cwd,namespace):
                yield solution
    elif isinstance(expr,Import):
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
        self.engine = expressions
        self.name = name
        self.namespace = namespace
    def resolve_all(self,**bindings):
        """Iterate over all solutions, and include bindings with each solution"""
        for solution in resolve(self.engine, bindings, namespace=self.namespace):
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
