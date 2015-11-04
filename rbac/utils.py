from oii.ioutils import upload
from oii.rbac import AUTHORIZATION_HEADER

def secure_upload(path,url,api_key):
    return upload(path,url,headers={
        AUTHORIZATION_HEADER: 'Bearer %s' % api_key
    })

