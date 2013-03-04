# -*- coding: utf-8 -*-

import logging
from datetime import datetime, timedelta
from functools import partial
from collections import namedtuple

from whoosh.query import Term, DateRange

from .exceptions import PageNotFound


_log = logging.getLogger(__name__)


PageInfo = namedtuple(
    'PageInfo',
    'date slug ref title status blob_id',
)

PageInfo.to_url = lambda self: '/page/%04d/%02d/%02d/%s' % (
    self.date.year,
    self.date.month,
    self.date.day,
    self.slug,
)


class Page(object):

    def __init__(self, slug, ref, blob_id, doc):
        self.slug = slug
        self.ref = ref
        self.blob_id = blob_id
        self.doc = doc


class GitPages(object):

    _max_timedelta = timedelta(days=1)
    _default_statuses = frozenset(u'published')

    def __init__(self, repo, date_index, history_index):
        self._repo = repo
        self._date_index = date_index
        self._history_index = history_index

    def page(self, date, slug, ref):

        earliest = datetime(date.year, date.month, date.day)
        latest = earliest + GitPages._max_timedelta

        query = (
            Term('slug', unicode(slug)) &
            DateRange(
                'date',
                start=earliest,
                end=latest,
                startexcl=False,
                endexcl=True,
            )
        )

        with self._date_index.searcher() as s:

            results = s.search(query)

            if results.is_empty():
                _log.debug('results is empty')
                raise PageNotFound(date, slug, ref)

            page_result = results[0]

            def get_blob(blob_id):
                return self._repo.get_blob(blob_id)

            blob_id = page_result['blob_id']
            blob = get_blob(blob_id)

            parts = partial(render_page_content, blob)

            return Page(slug, ref, blob_id, parts)

    def history(self, page):
        return page_history(page.slug)

    def older_pages(self, page):
        pass

    def newer_pages(self, page):
        pass

    def index(self, page_number, ref, page_length=10):

        query = Term('status', u'published')

        with self._date_index.searcher() as s:

            results = s.search_page(
                query,
                pagenum=page_number,
                pagelen=page_length,
                sortedby='date',
                reverse=True,
            )

            return [
                PageInfo(
                    date=r['date'],
                    slug=r['slug'],
                    ref=r['ref_id'],
                    title=r['title'],
                    status=r['status'],
                    blob_id=r['blob_id'],
                ) for r in results
            ]

    def teardown(self):

        try:
            self._date_index.close()
        except:
            pass

        try:
            self._history_index.close()
        except:
            pass


def render_page_content(blob):
    from docutils.core import publish_parts

    return publish_parts(
        source=blob.data,
        writer_name='html',
    )


def page_history(page_pk):
    import random

    length = random.randint(1, 20)

    return (
        'revision %d of page#%s' % (i, page_pk)
        for i in xrange(1, length + 1)
    )
