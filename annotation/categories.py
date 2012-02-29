
# abstract API for representing taxonomy
class Categories(object):
    def __init__(self):
        self.categories = [{
            "pid": "http://foo.bar/SomeTerm",
            "label": "Some Term"
        }]
    def list_categories(self):
        return self.categories
    def fetch_category(self,pid):
        for c in self.list_categories():
            if c['pid'] == pid:
                return c
        raise KeyError('no such category '+pid)