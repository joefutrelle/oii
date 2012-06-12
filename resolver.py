#!/usr/bin/python
from lxml import etree
from collections import namedtuple
import re
from glob import iglob
from os import path

# "little language" pattern

Match = namedtuple('Match', ['variable','regex'])
Variable = namedtuple('Variable', ['name','values'])
Path = namedtuple('Path', ['variable', 'match', 'expressions'])

# convert XML format into named tuple representation.
# a resolver is a sequence of expressions, each of which is
# either a Match, Variable, or Path expression.
def sub_parse(node):
    for child in node:
        if child.tag == 'match':
            yield Match(variable=child.get('variable'), regex=child.text)
        elif child.tag == 'variable':
            values = [gc.text for gc in child if gc.tag == 'value'];
            if not values:
                values = [child.text]
            yield Variable(name=child.get('name'), values=values)
        elif child.tag == 'path':
            yield Path(variable=child.get('variable'), match=child.get('match'), expressions=list(sub_parse(child)))

# parsing entry point
def parse(pathname):
    r = etree.parse(pathname).getroot()
    return list(sub_parse(r))

# substitute patterns like ${varname} for their values given
# a dict of varname->value
def substitute(template,bindings):
    result = template
    for key,value in bindings.items():
        result = re.sub('\$\{'+key+'\}',value,result)
    return result

# recursive resolution engine that handles one expression
# resolver - parsed resolution script
# bindings - variable name -> value mappings
# cwd - current working directory (recursively descends)
# yields hits, that is, files that the pid resolves to
def resolve(resolver,bindings,cwd='/'):
    if not resolver: # no more expressions left?
        return
    expr = resolver[0] # work on the first one
    print expr
    if isinstance(expr,Match):
        # "match" means test a variable against a regex, and (optionally) match groups
        # group n will be bound to ${n+1}, so for instance if variable
        # "foo" is "yes,no,123" then
        # <match variable="foo">([a-z]+),([a-z]+),(\d+)</match>
        # will add the following bindings
        # ${1} -> "yes"
        # ${2} -> "no"
        # ${3} -> "123"
        # if there is no match, execution stops
        value = bindings[expr.variable]
        m = re.match(substitute(expr.regex,bindings), value)
        if m is not None:
            groups = m.groups()
            local_bindings = bindings.copy()
            for index,group in zip(range(len(groups)), groups):
                local_bindings[str(index+1)] = group
            # done, now do the rest of the resolver
            for hit in resolve(resolver[1:],local_bindings,cwd):
                yield hit
    elif isinstance(expr,Variable):
        # "variable" means bind a variable from a template that may optionally
        # include variable references. So if ${3} is bound to "foo",
        # <variable name="fb">${3}bar</variable>
        # will add the binding
        # ${fb} -> "foobar"
        # if the variable has multiple "value" sub-elements, those will be
        # bound one at a time, and the rest of the resolver will be evaluated
        # for each binding. So for example
        # <variable name="fb">
        #   <value>${3}bar</value>
        #   <value>${3} fighters</value>
        # </variable>
        # will evaluate the rest of the resolver, first with ${fb} bound to "foobar",
        # and then with ${fb} bound to "foo fighters"
        name = expr.name
        for template in expr.values:
            local_bindings = bindings.copy()
            local_bindings[name] = substitute(template,bindings)
            # done, now do the rest of the resolver
            for hit in resolve(resolver[1:],local_bindings,cwd):
                yield hit
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
        # <path variable="service" match="/etc/rc*.d/*">
        #   <match variable="service">/etc/rc\d.d/([A-Z]\d+)${pid}</match>
        #   <path match="${service}"/>
        # </path>
        # will resolve to paths like /etc/rc0.d/K02apache2, but not paths like
        # /etc/rc0.d/README or /etc/rcS.d/K99apache2
        variable = expr.variable
        candidate = path.join(cwd, substitute(expr.match,bindings))
        if variable is None and path.exists(candidate) and path.isfile(candidate):
            yield candidate
        else:
            for hit in iglob(candidate):
                local_bindings = bindings.copy()
                if variable is not None:
                    local_bindings[variable] = hit
                # done, now evaluate the inner resolver if any
                for h in resolve(expr.expressions, local_bindings, hit):
                    yield h

# example configuration
# this takes pids like
#   UNQ.20110621.153252431.1423
# pathnames like
#   /mnt/nmfs-2/webdata/HabCam/data/Cruises/HS_20110621/Images/Full/20110621_1530/UNQ.20110621.153252431.1423.jpg
#
# <resolver name="habcam-jpg">
#     <match variable="pid">([A-Z]+\.((\d{4})\d{4})\.(\d{3}).*)</match>
#     <variable name="filename">${1}.jpg</variable>
#     <variable name="day">${2}</variable>
#     <variable name="year">${3}</variable>
#     <variable name="img_dir">${day}_${4}0</variable>
#     <variable name="root">/mnt/nmfs-2/webdata/HabCam/data/Cruises</variable>
#     <path variable="cruise_dir" match="${root}/*">
#         <match variable="cruise_dir">.*/[A-Z]{2}_\d+</match>
#         <path match="Images/Full/${img_dir}/${filename}"/>
#     </path>
# </resolver>

# note that the computation of the name of the ten minute directory in
# this case can be done as a text substitution.  if arithmetic is
# required, this class doesn't currently support any such operations.
