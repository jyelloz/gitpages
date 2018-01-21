# -*- coding: utf-8 -*-

import logging
import re
from datetime import datetime, timedelta
from functools import partial
from collections import namedtuple

from flask import url_for
from whoosh.query import Term, DateRange, And, Or, NestedChildren, Every

from .exceptions import PageNotFound, AttachmentNotFound
from ..util import cached


_log = logging.getLogger(__name__)
_content_disposition_expression = re.compile(
    r'^.*;\s*filename=(.+?)(:?;\s*.*)*$'
)

_PageInfo = namedtuple(
    'PageInfo',
    'date slug ref title status blob_id path revision_date revision_slug',
)
_Page = namedtuple('Page', 'info doc')
_PageAttachmentMetadata = namedtuple(
    'PageAttachmentMetadata',
    'attachment_id content_type content_disposition content_length',
)
_PageAttachment = namedtuple(
    'PageAttachment',
    'metadata data',
)

class PageInfo(_PageInfo):

    def to_url(self, _external=False):
        return url_for(
            '.page_archive_view',
            year=self.date.year,
            month=self.date.month,
            day=self.date.day,
            slug=self.slug,
            _external=_external,
        )

    def to_url_tree(self, tree_id, _external=False):
        return url_for(
            '.page_archive_view_ref',
            tree_id=tree_id,
            year=self.date.year,
            month=self.date.month,
            day=self.date.day,
            slug=self.slug,
            _external=_external,
        )


class Page(_Page):

    def to_url(self, _external=False):
        return self.info.to_url(_external=_external)

    def to_url_tree(self, tree_id, _external=False):
        return self.info.to_url_tree(tree_id, _external=_external)


class PageAttachmentMetadata(_PageAttachmentMetadata):

    def to_url(self, attachment=True, _external=False):
        return url_for(
            '.attachment' if attachment else '.inline_attachment',
            tree_id=self.attachment_id,
            _external=_external,
        )

    @property
    def filename(self):

        match = _content_disposition_expression.match(
            self.content_disposition
        )

        return (
            match.group(1) if match
            else self.attachment_id + '.bin'
        )


class PageAttachment(_PageAttachment):

    @property
    def filename(self):
        return self.metadata.filename

    def to_url(self, attachment=True, _external=False):
        return self.metadata.to_url(
            attachment,
            _external=False,
        )


def statuses_query(status_field_prefix, statuses):
    field_name = status_field_prefix + '_status'
    return Or([Term(field_name, s) for s in statuses])


def _to_bytes(s):
    return s.encode('ascii')


def _get_page_blob_id(result):
    return _to_bytes(result['page_blob_id'])


def _get_attachement_data_blob_id(result):
    return _to_bytes(result['attachment_data_blob_id'])


class GitPages(object):

    _max_timedelta = timedelta(days=1)
    _default_statuses = frozenset(('published',))

    def __init__(self, repo, searcher):
        self._repo = repo
        self._searcher = searcher

    @classmethod
    def _load_page_info(cls, result):

        return PageInfo(
            slug=result['page_slug'],
            ref=None,
            blob_id=result['page_blob_id'],
            date=result['page_date'],
            title=result['page_title'],
            status=result['page_status'],
            path=result['page_path'],
            revision_slug=result['page_slug'],
            revision_date=result['page_date'],
        )

    @classmethod
    def _load_page_revision_info(cls, page_result, page_revision_result):

        return PageInfo(
            slug=page_result['page_slug'],
            date=page_result['page_date'],
            ref=page_revision_result['revision_tree_id'],
            blob_id=page_revision_result['revision_blob_id'],
            title=page_revision_result['revision_title'],
            status=page_revision_result['revision_status'],
            path=page_revision_result['revision_path'],
            revision_slug=page_revision_result['revision_slug'],
            revision_date=page_revision_result['revision_date'],
        )

    @classmethod
    def _load_page(cls, result, parts):
        return Page(
            info=cls._load_page_info(result),
            doc=parts,
        )

    @classmethod
    def _load_page_revision(cls, page_result, page_revision_result, parts):
        return Page(
            info=cls._load_page_revision_info(
                page_result,
                page_revision_result,
            ),
            doc=parts,
        )

    @classmethod
    def _load_attachment(cls, repo, result):

        metadata = PageAttachmentMetadata(
            attachment_id=result['attachment_id'],
            content_type=result['attachment_content_type'],
            content_disposition=result['attachment_content_disposition'],
            content_length=result['attachment_content_length'],
        )

        attachment_data_blob_id = _get_attachement_data_blob_id(result)

        data = partial(
            repo.__getitem__,
            attachment_data_blob_id,
        )

        return PageAttachment(
            metadata=metadata,
            data=data,
        )

    def page_by_path(self, path):

        results = self._searcher.search(
            Term('kind', 'page') & Term('page_path', path),
            limit=1,
        )

        if results.is_empty():
            raise PageNotFound(path)

        page_result = next(iter(results))

        page_blob_id_bytes = _get_page_blob_id(page_result)

        blob = self._repo.get_object(page_blob_id_bytes)

        parts = partial(render_page_content, blob)

        return self._load_page(
            page_result,
            parts,
        )

    def page(self, date, slug, tree_id=None, statuses=_default_statuses):

        earliest = datetime(date.year, date.month, date.day)
        latest = earliest + self._max_timedelta

        statuses_clause = statuses_query('page', statuses)

        query = (
            Term('kind', 'page') &
            Term('page_slug', slug) &
            statuses_clause &
            DateRange(
                'page_date',
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

            blob_id = _get_page_blob_id(page_result)
            blob = self._repo.get_object(blob_id)

            parts = partial(render_page_content, blob)

            return self._load_page(
                page_result,
                parts,
            )

        pq = Term('kind', 'page')
        cq = Term('page_path', page_result['page_path']) & statuses_clause

        q = And([
            NestedChildren(pq, cq),
            Term('revision_tree_id', tree_id),
            statuses_query('revision', statuses),
        ])

        historic_results = self._searcher.search(q)

        page_revision_result = next(iter(historic_results))

        blob_id = page_revision_result['revision_blob_id']
        blob = self._repo.get_object(blob_id)

        parts = partial(render_page_content, blob)

        return self._load_page_revision(
            page_result,
            page_revision_result,
            parts,
        )

    def history(
        self,
        page,
        page_number,
        page_length=10,
        statuses=_default_statuses,
    ):

        path = page.info.path

        statuses_clause = statuses_query('page', statuses)
        revision_statuses_clause = statuses_query('revision', statuses)

        pq = Term('kind', 'page')
        cq = Term('page_path', path) & statuses_clause

        q = And([
            NestedChildren(pq, cq),
            Term('kind', 'revision'),
            revision_statuses_clause,
        ])

        results = self._searcher.search_page(
            q,
            pagenum=page_number,
            pagelen=page_length,
            sortedby='revision_commit_time',
            reverse=True,
        )

        return results

    def attachment(self, attachment_id):

        # FIXME: make it impossible to load attachments whose latest commit's
        # page is not publicly visible

        q = And([
            Term('kind', 'page-attachment')
            | Term('kind', 'revision-attachment'),
            Term('attachment_id', attachment_id),
        ])

        results = self._searcher.search(q)

        if results.is_empty():
            _log.debug('results is empty')
            raise AttachmentNotFound(attachment_id)

        result = next(iter(results))

        data_blob_id = _get_attachement_data_blob_id(result)

        metadata = PageAttachmentMetadata(
            attachment_id=result['attachment_id'],
            content_type=result['attachment_content_type'],
            content_disposition=result['attachment_content_disposition'],
            content_length=result['attachment_content_length'],
        )
        attachment = PageAttachment(
            metadata=metadata,
            data=partial(
                self._repo.get_object,
                data_blob_id,
            ),
        )

        return attachment

    def attachments(
        self,
        date,
        slug,
        tree_id=None,
        statuses=_default_statuses
    ):

        earliest = datetime(date.year, date.month, date.day)
        latest = earliest + self._max_timedelta

        page_kind, attachment_kind = (
            ('page', 'page-attachment') if tree_id is None
            else ('revision', 'revision-attachment')
        )

        statuses_clause = (
            statuses_query(page_kind, statuses)
            if statuses is not None and len(statuses)
            else Every()
        )

        pq = Term('kind', page_kind)
        cq = And([
            Term(page_kind + '_slug', slug),
            DateRange(
                page_kind + '_date',
                start=earliest,
                end=latest,
                startexcl=False,
                endexcl=True,
            ),
            statuses_clause,
        ])

        if tree_id is not None:
            cq = cq & Term(page_kind + '_tree_id', tree_id)

        q = And([
            NestedChildren(pq, cq),
            Term('kind', attachment_kind),
        ])

        results = self._searcher.search(q)

        if results.is_empty():
            return []

        return (
            self._load_attachment(self._repo, r)
            for r in results
        )

    def attachments_by_path(self, path, tree_id=None):

        page_kind, attachment_kind = (
            ('page', 'page-attachment') if tree_id is None
            else ('revision', 'revision-attachment')
        )

        pq = Term('kind', page_kind)
        cq = Term(page_kind + '_path', path)

        q = And([
            NestedChildren(pq, cq),
            Term('kind', attachment_kind),
        ])

        results = self._searcher.search(q)

        return (
            self._load_attachment(self._repo, r)
            for r in results
        )

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
            Term('kind', 'page') &
            statuses_query('page', statuses) &
            DateRange(
                'page_date',
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
            sortedby='page_date',
            reverse=True,
        )

        return (
            self._load_page_info(r)
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
            Term('kind', 'page') &
            statuses_query('page', statuses) &
            DateRange(
                'page_date',
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
            sortedby='page_date',
            reverse=False,
        )

        return (
            self._load_page_info(r)
            for r in results
        )

    def recent_pages(
        self, page_number, page_length, statuses=_default_statuses
    ):

        query = Term('kind', 'page') & statuses_query('page', statuses)

        results = self._searcher.search_page(
            query,
            page_number,
            page_length,
            sortedby='page_date',
            reverse=True,
        )

        return (
            self._load_page_info(r)
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

        status_clause = statuses_query('page', statuses)

        if start_date is None or end_date is None:

            query = status_clause

        else:

            query = status_clause & DateRange(
                'page_date',
                start=start_date,
                end=end_date,
                startexcl=bool(start_date_excl),
                endexcl=bool(end_date_excl),
            )

        repo = self._repo

        results = self._searcher.search_page(
            Term('kind', 'page') & query,
            pagenum=page_number,
            pagelen=page_length,
            sortedby='page_date',
            reverse=True,
        )

        results_blob_ids = (
            (r, _get_page_blob_id(r))
            for r in results
        )

        results_blobs = (
            (r, repo.get_object(page_blob_id))
            for r, page_blob_id in results_blob_ids
        )

        results_parts = (
            (r, partial(render_page_content, blob))
            for r, blob in results_blobs
        )

        return (
            self._load_page(r, parts)
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
