from oii.utils import dict_slice
        
# abstract API for representing assignments
class AssignmentStore(object):
    def ___init__(self):
        self.assignments = [{
            "pid": "http://foo.bar/assignments/baz",
            "label": "Identify quux for images from fnord cruise",
            "annotator": "Ann O. Tator",
            "status": "new",
            "mode": "quux",
            "images": [{
                 "pid": "http://foo.bar/images/abcdef",
                 "image": "http://foo.bar/images/abcdef.jpg"
            }]
	}]
        self.idmodes = [{
            "idmode_id": "http://foo.bar/assignments/1",
            "idmode_name": "fish,scallops,highlights"
        }]
        
    def list_assignments(self):
        for ass in self.assignments:
            yield dict_slice(ass,'pid,label,annotator,status,mode,images')
    def fetch_assignment(self,pid):
        for a in self.list_assignments():
            if a['pid'] == pid:
                return a
    def list_images(self,pid,limit=None,offset=0,status=None):
        return self.fetch_assignment(pid)['images']
    def find_image(self,pid,offset,status,post_status=None):
        return '0'
    def set_status(self,assignment_id,image_id,status):
        pass

