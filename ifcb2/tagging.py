import re

from sqlalchemy.exc import IntegrityError
from sqlalchemy import func, distinct

from oii.ifcb2.orm import Bin, BinTag

def normalize_tag(tagname):
    return re.sub(r'[^\w ]','',tagname.lower())
    
class Tagging(object):
    def __init__(self, session, ts_label=None):
        self.session = session
        self.ts_label = ts_label
    def _commit(self, commit):
        if not commit:
            return
        try:
            self.session.commit()
        except IntegrityError:
            self.session.rollback()
            raise
    def add_tag(self, b, tag, user_email=None, commit=True):
        """add a tag to a bin."""
        # head off duplicates
        tag_name = normalize_tag(tag)
        tag = BinTag(tag=tag_name, user_email=user_email)
        if tag not in b.tags:
            b.bintags.append(tag)
            self._commit(commit)
    def remove_tag(self, b, tag, commit=True):
        b.tags.remove(normalize_tag(tag))
        self._commit(commit)
    def tag_cloud(self):
        """get a dict of tags and frequency for a given time series"""
        rows = self.session.query(BinTag.tag, func.count(BinTag.tag)).\
            join(Bin).\
            filter(Bin.ts_label.like(self.ts_label)).\
            group_by(BinTag.tag, Bin.ts_label)
        return dict(list(rows))
    def search_tags_all(self, tag_names):
        """find all bins that have all tags"""
        q = self.session.query(Bin).\
            filter(Bin.ts_label.like(self.ts_label))
        for tag_name in tag_names:
            tag_name = normalize_tag(tag_name)
            q = q.filter(Bin.tags.contains(tag_name))
        q = q.order_by(Bin.sample_time.desc())
        return q
    def autocomplete(self, tag_stem):
        """autocomplete a tag; this query is NOT specific to one timeseries"""
        rows = self.session.query(distinct(BinTag.tag)).\
            filter(BinTag.tag.like('%s%%' % tag_stem)).\
            order_by(BinTag.tag)
        return list([row[0] for row in rows])
