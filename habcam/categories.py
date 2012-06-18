import psycopg2 as psql
from oii.config import get_config
from oii.annotation.categories import Categories

"""SELECT distinct classes.class_id,class_name,facets.facet_id,facet_name,scopes.scope_id,scope_name,idmode_id,idmode_name 
    FROM facets,scopes,classes,idmodes
    WHERE facets.scope_id = scopes.scope_id
        AND classes.facet_id = facets.facet_id
        AND idmodes.class_id = classes.class_id
        AND NOT classes.deprecated

        --the variables you might want to insert
        AND scopes.scope_id = 1 -- for target
        AND facets.facet_id = 1 -- for "categories" --optional
        AND idmode_id = 1 --for "fish scallops didemnum and highlights"        
ORDER BY facets.facet_id,class_name ;  --order by facet then alphabetical 
"""

class HabcamCategories(Categories):
    def __init__(self,config):
        self.config = config
    def list_categories(self,mode,scope=None):
        connection = psql.connect(self.config.psql_connect)
        cursor = connection.cursor()
        query = """
SELECT distinct classes.class_id,class_name,facets.facet_id,facet_name,scopes.scope_id,scope_name,idmode_id,idmode_name 
    FROM facets,scopes,classes,idmodes
    WHERE facets.scope_id = scopes.scope_id
        AND classes.facet_id = facets.facet_id
        AND idmodes.class_id = classes.class_id
        AND NOT classes.deprecated
        %s
        AND idmode_id = %s --for "fish scallops didemnum and highlights"        
ORDER BY facets.facet_id,class_name ;  --order by facet then alphabetical 
"""
        if scope is not None:
            scope_clause = 'AND scopes.scope_id = %s'
            params = (scope, mode)
        else:
            scope_clause = ''
            params = (mode,)
        # ok the following looks weird but works because of psycopg2 'overloading' %s
        print query % (scope_clause,'%s'), params # FIXME debug
        cursor.execute(query % (scope_clause,'%s'), params)
        for row in cursor.fetchall():
            d = {}
            d['pid'] = self.config.category_namespace + str(row[0])
            d['label'] = row[1]
            yield d

if __name__=='__main__':
    config = get_config('habcam_annotation.conf')
    hc = HabcamCategories(config)
    for cat in hc.list_categories('QC_Fish'):
        print cat
