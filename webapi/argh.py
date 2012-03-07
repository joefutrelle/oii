from annotation import IfcbFeedAssignmentStore

store = IfcbFeedAssignmentStore()

for f in store.list_assignments():
    print f