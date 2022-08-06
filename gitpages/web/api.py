# -*- coding: utf-8 -*-

import logging
import re
from datetime import datetime, timedelta
from functools import partial
from typing import (
        Any,
        Callable,
        Dict,
        Iterable,
        Mapping,
        NamedTuple,
        Optional,
        Tuple,
)

from flask import url_for
from whoosh.query import Term, DateRange, And, Or, NestedChildren, Every

from dulwich.objects import Blob

from .exceptions import PageNotFound, AttachmentNotFound


_log = logging.getLogger(__name__)
_content_disposition_expression = re.compile(
    r'^.*;\s*filename=(.+?)(:?;\s*.*)*$'
)

DocutilsParts = Mapping[str, Any]
LazyDocutilsParts = Callable[[], DocutilsParts]

LazyBlob = Callable[[], Blob]

class PageInfo(NamedTuple):

    date: datetime
    slug: str
    ref: Optional[str]
    title: str
    status: str
    blob_id: str
    path: str
    revision_date: datetime
    revision_slug: str

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


class Page(NamedTuple):

    info: PageInfo
    doc: LazyDocutilsParts

    def to_url(self, _external=False):
        return self.info.to_url(_external=_external)

    def to_url_tree(self, tree_id, _external=False):
        return self.info.to_url_tree(tree_id, _external=_external)


class PageAttachmentMetadata(NamedTuple):

    attachment_id: str
    content_type: str
    content_disposition: str
    content_length: int

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


class PageAttachment(NamedTuple):

    metadata: PageAttachmentMetadata
    data: LazyBlob

    @property
    def filename(self) -> str:
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


def _get_attachement_data_blob_id(result):
    return _to_bytes(result['attachment_data_blob_id'])


class GitPages(object):

    _max_timedelta = timedelta(days=1)
    _default_statuses = frozenset(('published',))

    def __init__(self, repo, searcher):
        self._repo = repo
        self._searcher = searcher

    @classmethod
    def _load_page_info(cls, page: dict) -> PageInfo:
        return PageInfo(
            slug=page['page_slug'],
            ref=None,
            blob_id=page['page_blob_id'],
            date=page['page_date'],
            title=page['page_title'],
            status=page['page_status'],
            path=page['page_path'],
            revision_slug=page['page_slug'],
            revision_date=page['page_date'],
        )

    @classmethod
    def _load_page_revision_info(cls, page: dict, revision: dict) -> PageInfo:
        return PageInfo(
            slug=page['page_slug'],
            date=page['page_date'],
            ref=revision['revision_tree_id'],
            blob_id=revision['revision_blob_id'],
            title=revision['revision_title'],
            status=revision['revision_status'],
            path=revision['revision_path'],
            revision_slug=revision['revision_slug'],
            revision_date=revision['revision_date'],
        )

    @classmethod
    def _load_page(cls, result) -> Page:
        return Page(
            info=cls._load_page_info(result),
            doc=lambda: result['page_rendered'],
        )

    @classmethod
    def _load_page_revision(cls, page_result, page_revision_result) -> Page:
        return Page(
            info=cls._load_page_revision_info(
                page_result,
                page_revision_result,
            ),
            doc=lambda: page_revision_result['revision_rendered'],
        )

    @classmethod
    def _load_attachment(cls, repo, result) -> PageAttachment:

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

    def page_by_path(self, path) -> Page:

        results = self._searcher.search(
            Term('kind', 'page') & Term('page_path', path),
            limit=1,
        )

        if results.is_empty():
            raise PageNotFound(path)

        page_result = next(iter(results))

        return self._load_page(page_result)

    def page(
            self, date, slug, tree_id=None, statuses=_default_statuses,
    ) -> Page:

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
            return self._load_page(page_result)

        pq = Term('kind', 'page')
        cq = Term('page_path', page_result['page_path']) & statuses_clause

        q = And([
            NestedChildren(pq, cq),
            Term('revision_tree_id', tree_id),
            statuses_query('revision', statuses),
        ])

        historic_results = self._searcher.search(q)

        page_revision_result = next(iter(historic_results))

        return self._load_page_revision(
            page_result,
            page_revision_result,
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

    def attachment(self, attachment_id) -> PageAttachment:

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

        return PageAttachment(
            metadata=metadata,
            data=partial(
                self._repo.get_object,
                data_blob_id,
            ),
        )

    def attachments(
        self,
        date,
        slug,
        tree_id=None,
        statuses=_default_statuses
    ) -> Iterable[PageAttachment]:

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

    def attachments_by_path(
            self,
            path: str,
            tree_id=None,
    ) -> Iterable[PageAttachment]:

        page_kind, attachment_kind = (
            ('page', 'page-attachment') if tree_id is None
            else ('revision', 'revision-attachment')
        )

        pq = (
            Term('kind', page_kind) if tree_id is None
            else
            Term('kind', page_kind) & Term(page_kind + '_tree_id', tree_id)
        )
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
    ) -> Iterable[PageInfo]:

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
    ) -> Iterable[PageInfo]:

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
    ) -> Iterable[PageInfo]:

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
    ) -> Tuple[Iterable[Page], Iterable[Dict]]:

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

        results = self._searcher.search_page(
            Term('kind', 'page') & query,
            pagenum=page_number,
            pagelen=page_length,
            sortedby='page_date',
            reverse=True,
        )

        return (
            self._load_page(r)
            for r in results
        ), results

    def teardown(self):
        pass


def render_page_content(source: str) -> DocutilsParts:

    from docutils.core import publish_parts
    from gitpages.web.rst import GitPagesWriter

    return publish_parts(
        source=source,
        writer=GitPagesWriter(),
        settings_overrides={
            'initial_header_level': 3,
            'syntax_highlight': 'short',
            'smart_quotes': True,
        },
    )
