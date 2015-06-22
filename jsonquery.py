import sys
import re
import json

# internal function, do not call directly
def _jsonquery(J, exprs):
    try: # pop the first expression
        expr = exprs[0]
        exprs = exprs[1:]
    except IndexError: # or note terminal case
        expr = None
    def recur(Js): # recurrence helper
        for s in _jsonquery(Js, exprs):
            yield s
    # if we have a list, we descend into it,
    # optionally applying some selection criterion
    if isinstance(J, list):
        # first/last selectors
        if expr==':first':
            for s in recur(J[0]): yield s
        elif expr==':last':
            for s in recur(J[-1]): yield s
        # no selector, simply recur
        elif not expr:
            for Ji in J: # for each element in the list
                for s in recur(Ji): yield s
        else: # we have a selector
            try: # see if we've got a key=value selector
                k,v = re.split('=',expr)
                for Ji in J: # for each element in the list
                    # test if it has the key and it matches
                    if k in Ji and str(Ji[k])==v: # if so recur
                        for s in recur(Ji): yield s
            except: # we just have a dict key selector
                pass
            for Ji in J: # iterate over list
                if expr in Ji: # if it has the key
                    # recur on the value of the key
                    for s in recur(Ji[expr]): yield s
    # if we have a dict, then we either have a key selector
    # or we have a solution
    elif isinstance(J, dict):
        if expr in J: # we have a key selector, recur
            for s in recur(J[expr]): yield s
        else: # this must be a solution, yield it
            yield J
    # we have a value that is neither a dict nor a list
    else:
        # so just yield it
        yield J

def jsonquery(J, expr):
    """ query JSON. syntax:
    {key}         match a key from a dict
    {key}=value   match any dict with key=value
    {key}:first   if key refers to a list value, match the first item
    {key}:last    if key refers to a list value, match the last itme
    these expressions are chained together to descend a strucutre.
    for example given an IFCB bin JSON here are some meaningful expressions:
    "targets pid" - return a list of target URLs
    "targets:first pid" - return the first target URL
    "targets stitched=1 pid" - return a list of URLs of stitched targets
    "context" - return a list of lines in the context metadata field
    "context:first" - return the first line in the context metadata field
    """
    try:
        J = json.loads(J)
    except:
        pass # assume parsed structure is being passed in
    expr = re.sub(r'([:])',r' \1',expr)
    exprs = re.split('\s+',expr)
    for s in _jsonquery(J, exprs):
        yield s
