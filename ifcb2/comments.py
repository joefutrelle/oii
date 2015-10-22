from sqlalchemy import func

from oii.orm_utils import page_query
from oii.ifcb2.orm import Bin, BinComment

class Comments(object):
    def __init__(self, session, ts_label=None, page_size=25):
        self.session = session
        self.ts_label = ts_label
        self.page_size = page_size
    def search(self, search_string, page=0):
        tq = func.plainto_tsquery('english', search_string)
        q = self.session.query(BinComment)
        if self.ts_label is not None:
            q = q.join(Bin).filter(Bin.ts_label==self.ts_label)
        q = q.filter(BinComment.comment.op('@@')(tq))
        return page_query(q, page, self.page_size)
    def recent(self, page=0):
        q = self.session.query(BinComment).join(Bin).\
            filter(Bin.ts_label==self.ts_label).\
            order_by(BinComment.ts.desc())
        return page_query(q, page, self.page_size)
