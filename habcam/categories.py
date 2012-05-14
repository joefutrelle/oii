import psycopg2 as psql
from oii.config import get_config
from oii.annotation.categories import Categories

class HabcamCategories(Categories):
    def __init__(self,config):
        self.config = config
    def list_categories(self,mode):
        connection = psql.connect(self.config.psql_connect)
        cursor = connection.cursor()
        cursor.execute('select taxonomy.idcode, category_name, genus, species from node_children, taxonomy where nodelabel like %s and node_children.idcode = taxonomy.idcode and deprecated = false', (mode,))
        for row in cursor.fetchall():
            d = {}
            d['pid'] = self.config.category_namespace + str(row[0])
            d['label'] = row[1]
            d['genus'] = row[2]
            d['species'] = row[3]
            yield d

if __name__=='__main__':
    config = get_config('habcam_annotation.conf')
    hc = HabcamCategories(config)
    for cat in hc.list_categories('QC_Fish'):
        print cat
