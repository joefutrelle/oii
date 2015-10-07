from sqlalchemy.exc import IntegrityError
from sqlalchemy import func

from oii.ifcb2.orm import Bin, BinTag

class Tagging(object):
    def __init__(self, session):
        self.session = session
    def _commit(self, commit):
        if not commit:
            return
        try:
            self.session.commit()
        except IntegrityError:
            self.session.rollback()
    def tag(self, b, tag, commit=True):
        """add a tag to a bin."""
        # head off duplicates
        if tag not in b.tags:
            b.tags.append(tag)
            self._commit(commit)
    def untag(self, b, tag, commit=True):
        """remove a tag from a bin"""
        b.tags.remove(tag)
        self._commit(commit)
    def tag_cloud(self, ts_label):
        """get a dict of tags and frequency for a given time series"""
        rows = self.session.query(BinTag.tag, func.count(BinTag.tag)).\
            join(Bin).\
            filter(Bin.ts_label.like(ts_label)).\
            group_by(BinTag.tag, Bin.ts_label)
        return dict(list(rows))
