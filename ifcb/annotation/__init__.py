from oii.ifcb import client
from oii.annotation.assignments import AssignmentStore
from oii.annotation.categories import Categories

MVCO_MODE = 'http://ifcb-data.whoi.edu/modes/mvco/'
MVCO_CATEGORY_NAMESPACE = 'http://ifcb-data.whoi.edu/categories/mvco/'

# demonstration feed that uses the most recent n bins as the set of assignments
class IfcbFeedAssignmentStore(AssignmentStore):
    def list_assignments(self):
        for bin in client.list_bins():
            yield self.fetch_assignment(bin['pid'])
    def fetch_assignment(self,pid):
        bin = client.fetch_object(pid)
        return {
            'pid': pid,
            'label': bin['time'],
            'annotator': 'Ann O. Tator',
            'status': 'new',
            'mode': MVCO_MODE,
            'images': [dict(pid=i, image=i+'.jpg') for i in client.list_targets(pid)]
        }

mvco_cats = [
'Asterionellopsis',
'Cerataulina',
'Ceratium',
'Chaetoceros',
'Corethron',
'Coscinodiscus',
'Cylindrotheca',
'DactFragCerataul',
'Dactyliosolen',
'Dictyocha',
'Dinobryon',
'Dinophysis',
'Ditylum',
'Ephemera',
'Eucampia',
'Euglena',
'Gonyaulax',
'Guinardia',
'Guinardia_flaccida',
'Guinardia_striata',
'Gyrodinium',
'Hemiaulus',
'Laboea',
'Lauderia',
'Leptocylindrus',
'Licmophora',
'Myrionecta',
'Odontella',
'Paralia',
'Phaeocystis',
'Pleurosigma',
'Prorocentrum',
'Pseudonitzschia',
'Pyramimonas',
'Rhizosolenia',
'Skeletonema',
'Stephanopyxis',
'Thalassionema',
'Thalassiosira',
'Thalassiosira_dirty',
'bad',
'ciliate',
'ciliate_mix',
'clusterflagellate',
'crypto',
'detritus',
'dino30',
'flagellate',
'kiteflagellates',
'mix',
'mix_elongated',
'not_ciliate',
'other',
'pennate',
'roundCell',
'tintinnid'
]

class IfcbCategories(Categories):
    def list_categories(self,mode):
        if mode == MVCO_MODE:
            for cat in mvco_cats:
                yield {
                    'pid': MVCO_CATEGORY_NAMESPACE + cat,
                    'label': cat,
                    'modes': [MVCO_MODE]
                }