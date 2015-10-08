from sqlalchemy.exc import IntegrityError
from sqlalchemy import func

from oii.ifcb2.orm import Bin, BinTag

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
    def add_tag(self, b, tag, commit=True):
        """add a tag to a bin."""
        # head off duplicates
        if tag not in b.tags:
            b.tags.append(tag)
            self._commit(commit)
    def remove_tag(self, b, tag, commit=True):
        """remove a tag from a bin"""
        b.tags.remove(tag)
        self._commit(commit)
    def tag_cloud(self):
        """get a dict of tags and frequency for a given time series"""
        rows = self.session.query(BinTag.tag, func.count(BinTag.tag)).\
            join(Bin).\
            filter(Bin.ts_label.like(self.ts_label)).\
            group_by(BinTag.tag, Bin.ts_label)
        return dict(list(rows))
    def search_tags_all(self, tag_names):
        q = self.session.query(Bin).\
            filter(Bin.ts_label.like(self.ts_label))
        for tag_name in tag_names:
            q = q.filter(Bin.tags.contains(tag_name))
        q = q.order_by(Bin.sample_time.desc())
        return q
