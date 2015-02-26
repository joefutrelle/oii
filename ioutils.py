import requests

def isok(r):
    return r.status_code < 400

def download(url,path):
    r = requests.get(url)
    if not isok(r):
        raise IOError('GET returned %d' % r.status_code)
    with open(path,'wb') as f:
        for chunk in r.iter_content(chunk_size=1024): 
            f.write(chunk)
            f.flush()

def upload(path,url):
    with open(path,'rb') as bi:
        bytez = bi.read() # read and pass bytes as data for 12.04 version of requests
        r = requests.put(url, data=bytez) 
        if not isok(r):
            raise IOError('PUT returned %d' % r.status_code)

def exists(url):
    r = requests.head(url)
    return isok(r)


