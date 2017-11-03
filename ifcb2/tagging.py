import re

from sqlalchemy.exc import IntegrityError
from sqlalchemy import func, distinct

from oii.orm_utils import page_query
from oii.ifcb2.orm import Bin, BinTag

def normalize_tag(tagname):
    return re.sub(r'[^\w ]','',tagname.lower())

def parse_ts_label_tags(ts_label_tags):
    if ts_label_tags is None:
        return None, None
    else:
        vals = re.split(':',ts_label_tags)
        ts_label, tags = vals[0], vals[1:]
        return ts_label, tags

def parse_ts_label_tag(ts_label_tag):
    ts_label, tags = parse_ts_label_tags(ts_label_tag)
    if not tags:
        return ts_label, None
    else:
        return ts_label, tags[0]

class Tagging(object):
    def __init__(self, session, ts_label=None, page_size=10):
        self.session = session
        self.ts_label, _ = parse_ts_label_tag(ts_label)
        self.page_size = page_size
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
    def tag_cloud(self, limit=25):
        """get a list of of tags and frequency for a given time series"""
        rows = self.session.query(BinTag.tag, func.count(BinTag.tag)).\
            join(Bin).\
            filter(Bin.ts_label.like(self.ts_label)).\
            group_by(BinTag.tag).\
            order_by(func.count(BinTag.tag).desc())[:limit]
        return [{
            'tag': row[0],
            'count': row[1]
        } for row in sorted(rows, key=lambda row: row[0])]
    def search_tags_all(self, tag_names, page=0, include_skip=False):
        """find all bins that have all tags"""
        q = self.session.query(Bin).\
            filter(Bin.ts_label.like(self.ts_label))
        if not include_skip:
            q = q.filter(~Bin.skip)
        for tag_name in tag_names:
            tag_name = normalize_tag(tag_name)
            q = q.filter(Bin.tags.contains(tag_name))
        q = q.order_by(Bin.sample_time.desc())
        return page_query(q, page, self.page_size)
    def recent(self, page=0):
        q = self.session.query(BinTag).join(Bin).\
            filter(Bin.ts_label.like(self.ts_label)).\
            order_by(BinTag.ts.desc())
        return page_query(q, page, self.page_size)
    def autocomplete(self, tag_stem):
        """autocomplete a tag; this query is NOT specific to one timeseries"""
        rows = self.session.query(distinct(BinTag.tag)).\
            filter(BinTag.tag.like('%s%%' % tag_stem)).\
            order_by(BinTag.tag)
        return list([row[0] for row in rows])
