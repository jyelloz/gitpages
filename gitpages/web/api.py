# -*- coding: utf-8 -*-

import logging
from datetime import datetime, timedelta
from functools import partial

from whoosh.query import Term, DateRange

from .exceptions import PageNotFound


_log = logging.getLogger(__name__)


class Page(object):

    def __init__(self, slug, ref, doc):
        self.slug = slug
        self.ref = ref
        self.doc = doc


class GitPages(object):

    _max_timedelta = timedelta(days=1)

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

            blob = get_blob(blob_id=page_result['blob_id'])

            parts = partial(render_page_content, blob)

            return Page(slug, ref, parts)

    def history(self, page):
        return page_history(page.slug)

    def older_pages(self, page):
        pass

    def newer_pages(self, page):
        pass

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
