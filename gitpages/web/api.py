# -*- coding: utf-8 -*-

import logging
from datetime import datetime, timedelta
from functools import partial
from collections import namedtuple

from flask import url_for
from whoosh.query import Term, DateRange, Or

from .exceptions import PageNotFound
from ..util import cached


_log = logging.getLogger(__name__)


PageInfo = namedtuple(
    'PageInfo',
    'date slug ref title status blob_id',
)

PageInfo.to_url = lambda self: url_for(
    '.page_archive_view',
    year=self.date.year,
    month=self.date.month,
    day=self.date.day,
    slug=self.slug,
)


Page = namedtuple(
    'Page',
    'info doc',
)

Page.to_url = lambda self: self.info.to_url()


class GitPages(object):

    _max_timedelta = timedelta(days=1)
    _default_statuses = frozenset((u'published',))

    def __init__(self, repo, date_searcher, history_searcher):
        self._repo = repo
        self._date_searcher = date_searcher
        self._history_searcher = history_searcher

    @staticmethod
    def _load_page_info(result):

        return PageInfo(
            slug=result['slug'],
            ref=result['ref_id'],
            blob_id=result['blob_id'],
            date=result['date'],
            title=result['title'],
            status=result['status'],
        )

    @staticmethod
    def _load_page(result, parts):

        return Page(
            info=GitPages._load_page_info(result),
            doc=parts,
        )

    def page(self, date, slug, ref, statuses=_default_statuses):

        earliest = datetime(date.year, date.month, date.day)
        latest = earliest + GitPages._max_timedelta

        query = (
            Term('slug', unicode(slug)) &
            Or(Term('status', s) for s in statuses) &
            DateRange(
                'date',
                start=earliest,
                end=latest,
                startexcl=False,
                endexcl=True,
            )
        )

        results = self._date_searcher.search(query)

        if results.is_empty():
            _log.debug('results is empty')
            raise PageNotFound(date, slug, ref)

        page_result = results[0]

        blob_id = page_result['blob_id']
        blob = self._repo.get_blob(blob_id)

        parts = partial(render_page_content, blob)

        return GitPages._load_page(page_result, parts)

    def history(self, page):
        return page_history(page.slug)

    def older_pages(self, page, page_number, ref, page_length=10):

        latest = page.info.date

        query = (
            Or(Term('status', s) for s in GitPages._default_statuses) &
            DateRange(
                'date',
                start=None,
                end=latest,
                startexcl=False,
                endexcl=True,
            )
        )

        results = self._date_searcher.search_page(
            query,
            pagenum=page_number,
            pagelen=page_length,
            sortedby='date',
            reverse=True,
        )

        return (
            GitPages._load_page_info(r)
            for r in results
        )

    def newer_pages(self, page, page_number, ref, page_length=10):

        earliest = page.info.date

        query = (
            Or(Term('status', s) for s in GitPages._default_statuses) &
            DateRange(
                'date',
                start=earliest,
                end=None,
                startexcl=True,
                endexcl=False,
            )
        )

        results = self._date_searcher.search_page(
            query,
            pagenum=page_number,
            pagelen=page_length,
            sortedby='date',
            reverse=False,
        )

        return (
            GitPages._load_page_info(r)
            for r in results
        )

    def index(self, page_number, ref, page_length=10):

        query = Or(Term('status', s) for s in GitPages._default_statuses)

        results = self._date_searcher.search_page(
            query,
            pagenum=page_number,
            pagelen=page_length,
            sortedby='date',
            reverse=True,
        )

        return (
            GitPages._load_page_info(r)
            for r in results
        )

    def teardown(self):
        pass


@cached(key='page/%s', key_builder=lambda blob: blob.id)
def render_page_content(blob):

    from docutils.core import publish_parts

    return publish_parts(
        source=blob.data,
        writer_name='html',
        settings_overrides={
            'initial_header_level': 3,
            'syntax_highlight': 'short',
            'smart_quotes': True,
        },
    )


def page_history(page_pk):
    import random

    length = random.randint(1, 20)

    return (
        'revision %d of page#%s' % (i, page_pk)
        for i in xrange(1, length + 1)
    )
