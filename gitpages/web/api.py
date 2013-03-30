# -*- coding: utf-8 -*-

import logging
from datetime import datetime, timedelta
from functools import partial
from collections import namedtuple

from flask import url_for
from whoosh.query import Term, DateRange, Or, NestedChildren

from .exceptions import PageNotFound
from ..util import cached


_log = logging.getLogger(__name__)


PageInfo = namedtuple(
    'PageInfo',
    'date slug ref title status blob_id path',
)

PageInfo.to_url = lambda self: url_for(
    '.page_archive_view',
    year=self.date.year,
    month=self.date.month,
    day=self.date.day,
    slug=self.slug,
)

PageInfo.to_url_tree = lambda self, tree_id: url_for(
    '.page_archive_view_ref',
    tree_id=tree_id,
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
Page.to_url_tree = lambda self, tree_id: self.info.to_url_tree(tree_id)


class GitPages(object):

    _max_timedelta = timedelta(days=1)
    _default_statuses = frozenset((u'published',))

    def __init__(self, repo, searcher):
        self._repo = repo
        self._searcher = searcher

    @staticmethod
    def _load_page_info(result):

        return PageInfo(
            slug=result['slug'],
            ref=None,  # result['ref_id'],
            blob_id=result['blob_id'],
            date=result['date'],
            title=result['title'],
            status=result['status'],
            path=result['path'],
        )

    @staticmethod
    def _load_page(result, parts):

        return Page(
            info=GitPages._load_page_info(result),
            doc=parts,
        )

    def by_path(self, path):

        results = self._searcher.search_page(
            Term('kind', u'page') & Term('path', path),
            pagenum=1,
            pagelen=1,
        )

        page_result = next(iter(results))

        blob = self._repo.get_blob(page_result['blob_id'])

        parts = partial(render_page_content, blob)

        return GitPages._load_page(page_result, parts)

    def page(self, date, slug, tree_id=None, statuses=_default_statuses):

        earliest = datetime(date.year, date.month, date.day)
        latest = earliest + GitPages._max_timedelta

        query = (
            Term('kind', u'page') &
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

        results = self._searcher.search(query)

        if results.is_empty():
            _log.debug('results is empty')
            raise PageNotFound(date, slug, tree_id)

        page_result = next(iter(results))

        if tree_id is None:
            blob_id = page_result['blob_id']
        else:

            pq = Term('kind', 'page')
            cq = Term('path', page_result['path'])
            q = (
                NestedChildren(pq, cq)
                # # Or(Term('status', s) for s in statuses) &
                # Term('tree_id', tree_id)
            )
            historic_results = self._searcher.search(
                q,
                # pagenum=1,
                # pagelen=1,
            )

            for r in historic_results:
                print r

            tree_id_matches = (r for r in historic_results if r['tree_id'] == tree_id)

            blob_id = next(tree_id_matches)['blob_id']

        blob = self._repo.get_blob(blob_id)

        parts = partial(render_page_content, blob)

        return GitPages._load_page(page_result, parts)

    def history(
        self,
        page,
        page_number,
        page_length=10,
        statuses=_default_statuses
    ):

        path = page.info.path

        pq = Term('kind', 'page')
        cq = Term('path', path)

        q = NestedChildren(pq, cq)
        # TODO: ensure the status of the post allows viewing

        results = self._searcher.search_page(
            q,
            pagenum=page_number,
            pagelen=page_length,
            sortedby='commit_time',
            reverse=True,
        )

        return results

    def older_pages(
        self,
        page,
        page_number,
        ref,
        page_length=10,
        statuses=_default_statuses,
    ):

        latest = page.info.date

        query = (
            Term('kind', u'page') &
            Or(Term('status', s) for s in statuses) &
            DateRange(
                'date',
                start=None,
                end=latest,
                startexcl=False,
                endexcl=True,
            )
        )

        results = self._searcher.search_page(
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

    def newer_pages(
        self,
        page,
        page_number,
        ref,
        page_length=10,
        statuses=_default_statuses,
    ):

        earliest = page.info.date

        query = (
            Term('kind', u'page') &
            Or(Term('status', s) for s in statuses) &
            DateRange(
                'date',
                start=earliest,
                end=None,
                startexcl=True,
                endexcl=False,
            )
        )

        results = self._searcher.search_page(
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

    def recent_pages(
        self, page_number, page_length, statuses=_default_statuses
    ):

        query = Term('kind', u'page') & Or(Term('status', s) for s in statuses)

        results = self._searcher.search_page(
            query,
            page_number,
            page_length,
            sortedby='date',
            reverse=True,
        )

        return (
            GitPages._load_page_info(r)
            for r in results
        )

    def index(
        self,
        page_number,
        ref,
        start_date=None,
        end_date=None,
        start_date_excl=False,
        end_date_excl=False,
        page_length=10,
        statuses=_default_statuses,
    ):

        status_clause = Or(Term('status', s) for s in statuses)

        if start_date is None or end_date is None:

            query = status_clause

        else:

            query = status_clause & DateRange(
                'date',
                start=start_date,
                end=end_date,
                startexcl=bool(start_date_excl),
                endexcl=bool(end_date_excl),
            )

        results = self._searcher.search_page(
            Term('kind', u'page') & query,
            pagenum=page_number,
            pagelen=page_length,
            sortedby='date',
            reverse=True,
        )

        results_blobs = (
            (r, self._repo.get_blob(r['blob_id']))
            for r in results
        )

        results_parts = (
            (r, partial(render_page_content, blob))
            for r, blob in results_blobs
        )

        return (
            GitPages._load_page(r, parts)
            for r, parts in results_parts
        ), results

    def teardown(self):
        pass


@cached(key='page/%s', key_builder=lambda blob: blob.id)
def render_page_content(blob):

    from docutils.core import publish_parts
    from gitpages.web.rst import GitPagesWriter

    return publish_parts(
        source=blob.data,
        writer=GitPagesWriter(),
        settings_overrides={
            'initial_header_level': 3,
            'syntax_highlight': 'short',
            'smart_quotes': True,
        },
    )
