class Scope(object):
   """a dict-like with a parent scope. bindings in lower scopes
   shadow bindings in ancestor scopes"""
   def __init__(self,bindings={},parent=None):
      """params
      bindings - initial local bindings that will shadow parent bindings
      parent - parent scope if any"""
      self.bindings = bindings
      self.parent = parent
   def __getitem__(self,key):
      """find value of item with given key,
      look in local bindings first, then recurse upward"""
      if key in self.bindings:
         return self.bindings[key]
      elif key in self.parent:
         return self.parent[key]
      else:
         raise KeyError
   def __setitem__(self,key,value):
      """set value in local bindings.
      will shadow same name in any ancestor scopes"""
      self.bindings[key] = value
   def __delitem__(self,key):
      """delete from local bindings, but allow shadowed values to remain"""
      del self.bindings[key]
   def __iter__(self):
      """iterate over keys from local and ancestor bindings"""
      for k in self.bindings.keys():
         yield k
      if not self.parent:
         return
      for k in self.parent:
         if k not in self.bindings.keys():
            yield k
   def __len__(self):
      """length of key set including ancestor keys"""
      return len(list(self.__iter__()))
   def __contains__(self,key):
      """is key contained in local or ancestor bindings"""
      if key in self.bindings:
         return True
      if self.parent and key in self.parent:
         return True
      return False
   def flatten(self):
      """return dict of all non-shadowed bindings"""
      return dict((k,self[k]) for k in self)
   def items(self):
      """return k,v of all non-shadowed bindings"""
      return self.flatten().items()
   def enclose(self,**kw):
      """generate a child scope with the given initial local bindings"""
      return Scope(parent=self,bindings=kw)
   def __repr__(self):
      """represent as if this is a flat dict"""
      return self.flatten().__repr__()
