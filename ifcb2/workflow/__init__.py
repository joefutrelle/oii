"""IFCB workflow components,
including workers for
- acquisition
- accession"""

import requests

from oii.ifcb2 import NAMESPACE
from oii.ifcb2.identifiers import parse_pid, PRODUCT

WILD_PRODUCT='wild'
RAW_PRODUCT='raw'
BINZIP_PRODUCT='binzip'
WEBCACHE_PRODUCT='webcache'
BLOBS_PRODUCT='blobs'
FEATURES_PRODUCT='features'

WILD2RAW='wild2raw'
RAW2BINZIP ='raw2binzip'
BINZIP2BLOBS ='binzip2blobs'
BINZIP2WEBCACHE = 'binzip2webcache'
BLOBS2FEATURES ='blobs2features'

def accepts_product(product_pid):
    parsed = parse_pid(product_pid)

    namespace = parsed[NAMESPACE]
    product = parsed[PRODUCT]
    
    ep = '%sapi/accepts_products/%s' % (namespace, product)
    
    try:
        return requests.get(ep).json()[product]
    except:
        return False

