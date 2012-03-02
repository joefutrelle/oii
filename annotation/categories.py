
# abstract API for representing multiple taxonomies
class Categories(object):
    def __init__(self):
        self.categories = [{
            "pid": "http://foo.bar/SomeTerm",
            "label": "Some Term",
            "modes": ["foo"]
        }]
    def list_modes(self):
        return ['foo']
    def list_categories(self,mode):
        for cat in self.categories:
            if mode in cat['modes']:
                yield cat
    def fetch_category(self,pid):
        for c in self.list_categories():
            if c['pid'] == pid:
                return c
        raise KeyError('no such category '+pid)