import re

from sqlalchemy.exc import IntegrityError
from sqlalchemy import func

from oii.ifcb2.orm import Bin, BinTag

def normalize_tag(tagname):
    return re.sub(r'[^\w ]','',tagname.lower())
    
class Tagging(object):
    def __init__(self, session, ts_label):
        self.session = session
        self.ts_label = ts_label
    def _commit(self, commit):
        if not commit:
            return
        try:
            self.session.commit()
        except IntegrityError:
            self.session.rollback()
    def add_tag(self, b, tag, user_email=None, commit=True):
        """add a tag to a bin."""
        # head off duplicates
        tag_name = normalize_tag(tag)
        tag = BinTag(tag=tag_name, user_email=user_email)
        if tag not in b.tags:
            b.bintags.append(tag)
            self._commit(commit)
    def remove_tag(self, b, tag, commit=True):
        """remove a tag from a bin"""
        tag = normalize_tag(tag)
        try:
            b.tags.remove(tag)
            self._commit(commit)
        except ValueError:
            pass
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
