from lxml import etree
import re

XML_FILE='oii/ldr.xml'

xml = etree.parse(XML_FILE)

# runtime scope represented as hieararchical dicts

def enclose(bindings,inner):
    inner['_parent'] = bindings
    return inner

def val(bindings,key):
    try:
        return bindings[key]
    except KeyError:
        try:
            return val(bindings['_parent'],key)
        except KeyError:
            return None

def keys(bindings):
    for k in bindings.keys():
        if k != '_parent':
            yield k
    try:
        for k in keys(bindings['_parent']):
            if k not in bindings.keys():
                yield k
    except KeyError:
        pass

def flatten(bindings):
    return dict((k,val(bindings,k)) for k in keys(bindings))

# namespace scoping
def find_names(e):
    def descend(e,namespace=[]):
        if e.tag=='namespace':
            sub_ns = namespace + [e.get('name')]
            yield sub_ns, e
            for se in e.findall('namespace'):
                for name, name_e in descend(se,namespace=sub_ns):
                    yield name, name_e
    return dict(('.'.join(n),ne) for n, ne in descend(e.getroot()))

global_ns = find_names(xml)

# substitute patterns like ${varname} for their values given
# bindings = a dict of varname->value
# e.g., substitute('${x}_${blaz}',{'x':'7','bork':'z','blaz':'quux'}) -> '7_quux'
def interpolate(template,bindings):
    result = template
    for key in keys(bindings):
        value = val(bindings,key)
        result = re.sub('\$\{'+key+'\}',value,result)
    return result

def evaluate_block(exprs,bindings={}):
    # recurrence expression establishes an inner scope and evaluates
    # the remaining expressions (which will yield solutions to the head expression)
    def recur(exprs,bindings,inner_bindings={}):
        return evaluate_block(exprs[1:],enclose(bindings,inner_bindings))
    # terminal case; all blocks yield all unfiltered solutions
    if len(exprs)==0:
        yield bindings
        return
    # handle the first expression
    expr = exprs[0]
    # The var expression sets variables to interpolated values
    # <var name="{name}">{value}</var>
    # <var name="{name}">
    #   <val>{value}</val>
    #   <val>{value}</val>
    # </var>
    if expr.tag=='var':
        var_name = expr.get('name')
        sub_val_exprs = expr.findall('val')
        if len(sub_val_exprs) == 0:
            var_val = interpolate(expr.text,bindings)
            for s in recur(exprs,bindings,{var_name:var_val}): yield s
        else:
            for sub_val_expr in sub_val_exprs:
                var_val = interpolate(sub_val_expr.text,bindings)
                for s in recur(exprs,bindings,{var_name:var_val}): yield s
    else:
        for s in recur(exprs,bindings): yield s
                
def evaluate(expr,bindings={}):
    if expr.tag == 'namespace':
        for solution in evaluate_block(list(expr),bindings=bindings):
            yield solution

ts = global_ns['mvco.time_series']
for s in evaluate(ts):
    print flatten(s)


    
