# -*- coding: utf-8 -*-

import functools
import posixpath
from typing import Any, Callable, Iterable, Generator, NamedTuple

from dulwich.repo import BaseRepo
from dulwich.objects import Blob, Tree, TreeEntry

from ..util.compat import (
    _text_to_bytes as _to_bytes,
    _bytes_to_text as _from_bytes,
)


PAGES_TREE, PAGE_RST = (
    u'page',
    u'page.rst',
)

PAGES_TREE_BYTES, PAGE_RST_BYTES = map(_to_bytes, (PAGES_TREE, PAGE_RST))

ATTACHMENTS_TREE, ATTACHMENT_METADATA_RST, ATTACHMENT_DATA = (
    b'attachment',
    b'metadata.rst',
    b'data',
)


class PageAttachment(NamedTuple):

    tree_id: bytes
    blob_id: bytes
    metadata_blob_id: bytes

    data_callable: Callable
    metadata_callable: Callable

    @property
    def tree_id_text(self) -> str:
        return _from_bytes(self.tree_id)

    @property
    def blob_id_text(self) -> str:
        return _from_bytes(self.blob_id)

    @property
    def metadata_blob_id_text(self) -> str:
        return _from_bytes(self.metadata_blob_id)

    @property
    def data(self):
        return self.data_callable()

    @property
    def metadata(self):
        return self.metadata_callable()


class PageRef(NamedTuple):
    path: str
    tree: Tree
    entry: TreeEntry


class Page(NamedTuple):
    path: str
    page: Blob
    attachments: Iterable[PageAttachment]


def get_pages_tree(
        repository: BaseRepo,
        ref: bytes=b'HEAD',
) -> Tree:

    ref_commit = repository[repository.refs[ref]]
    root = repository[ref_commit.tree]

    return repository[root[PAGES_TREE_BYTES][1]]


def find_pages(
        repository: BaseRepo,
        pages_tree: Tree,
        prefix=PAGES_TREE,
) -> Iterable[PageRef]:

    page_trees = (
        (_from_bytes(e.path), repository[e.sha])
        for e in pages_tree.iteritems()
    )

    page_trees_with_rst_entries = (
        (p, t, find_page_rst_entry(t))
        for (p, t) in page_trees
    )

    return (
        PageRef(
            posixpath.join(prefix, p, _from_bytes(rst.path)),
            t,
            rst
        )
        for (p, t, rst) in page_trees_with_rst_entries
    )


def load_pages_with_attachments(
        repository: BaseRepo,
        page_trees_with_rst,
) -> Generator[Page, None, None]:
    for path, page_tree, page_rst_entry in page_trees_with_rst:
        yield Page(
            path,
            load_page_data(repository, page_rst_entry),
            load_page_attachments(repository, page_tree),
        )


def find_page_rst_entry(page_tree: Tree) -> TreeEntry:

    return next(
        i for i in page_tree.iteritems()
        if i.path == PAGE_RST_BYTES
    )


def load_page_data(repository: BaseRepo, page_rst_entry: TreeEntry) -> Blob:
    return repository[page_rst_entry.sha]


def load_page_attachments(
        repository: BaseRepo,
        page_tree: Tree,
) -> Iterable[PageAttachment]:

    def load_page_attachment(attachment_tree: Tree) -> PageAttachment:

        data = next(
            i for i in attachment_tree.iteritems()
            if i.path == ATTACHMENT_DATA
        )
        metadata_rst = next(
            i for i in attachment_tree.iteritems()
            if i.path == ATTACHMENT_METADATA_RST
        )
        data_blob_id = data.sha
        metadata_blob_id = metadata_rst.sha

        data_callable = functools.partial(
            repository.__getitem__,
            data_blob_id,
        )
        metadata_callable = functools.partial(
            repository.__getitem__,
            metadata_blob_id,
        )

        return PageAttachment(
            attachment_tree.id,
            data_blob_id,
            metadata_blob_id,
            data_callable,
            metadata_callable,
        )

    attachments = next(
        (i for i in page_tree.iteritems() if i.path == ATTACHMENTS_TREE),
        None,
    )

    if attachments is None:
        return []

    page_attachments_tree = repository[attachments.sha]

    page_attachment_trees = (
        repository[t.sha] for t in page_attachments_tree.iteritems()
    )

    return (load_page_attachment(t) for t in page_attachment_trees)
