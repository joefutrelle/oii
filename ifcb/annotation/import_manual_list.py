from oii.psql import PsqlStore, xa
import sys
import os

#MOUNT_POINT = '/Volumes/d_work'
#DATA_DIR = os.path.join(MOUNT_POINT,'IFCB1','ifcb_data_mvco_jun06','Manual_fromClass','annotations_csv')
MOUNT_POINT = '/Users/jfutrelle/dev/ifcb'
DATA_DIR = os.path.join(MOUNT_POINT,'annotations_csv')
TEMP_DIR = '/tmp'

print 'copying file...'
csv = os.path.join(DATA_DIR,'manual_list.csv')
tmp = os.path.join(TEMP_DIR,'manual_list.csv')
os.system('cp %s %s' % (csv,tmp))

class ManualListStore(PsqlStore):
    def __init__(self,psql_connect):
        super(ManualListStore,self).__init__(psql_connect)
        self.TABLE_NAME = 'manual_list'
        self.SCHEMA = [
            ('lid', 'text', False),
            ('category', 'text', False),
            ('annotator', 'text', False)
        ]

psql_connect = sys.argv[1]
store = ManualListStore(psql_connect)
print 'creating table...'
store.create(False)
print 'bulk inserting...'
with xa(psql_connect) as (c,db):
    db.execute('copy manual_list from \'%s\' with csv' % tmp)
    print 'creating indexes...'
    store.create_indexes(c)
print 'done'
        
    
    