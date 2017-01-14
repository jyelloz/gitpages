# -*- coding: utf-8 -*-

import itertools
import functools
import posixpath
import six

PAGES_TREE, PAGE_RST = (
    'page',
    'page.rst',
)

ATTACHMENTS_TREE, ATTACHMENT_METADATA_RST, ATTACHMENT_DATA = (
    'attachment',
    'metadata.rst',
    'data',
)


def iterable_nth(iterable, n, default=None):
    return next(itertools.islice(iterable, n, None), default)


def get_pages_tree(repository, ref='HEAD', commit=None):

    if commit is None:
        ref_commit = repository[repository.refs[ref]]
        root = repository[ref_commit.tree]
    else:
        root = repository[commit.tree]

    return repository[root[PAGES_TREE][1]]


def find_pages(repository, pages_tree, prefix=PAGES_TREE):

    page_entries = six.iteritems(pages_tree)

    page_trees = ((e.path, repository[e.sha]) for e in page_entries)

    page_trees_with_rst_entries = (
        (p, t, find_page_rst_entry(t))
        for (p, t) in page_trees
    )

    return (
        (posixpath.join(prefix, p, rst.path), t, rst)
        for (p, t, rst) in page_trees_with_rst_entries
    )


def load_pages_with_attachments(repository, page_trees_with_rst):
    return (
        (
            path,
            load_page_data(repository, page_rst_entry),
            load_page_attachments(repository, page_tree),
        )
        for (path, page_tree, page_rst_entry) in page_trees_with_rst
    )


def find_page_rst_entry(page_tree):

    return next(
        i for i in six.iteritems(page_tree)
        if i.path == PAGE_RST
    )


def load_page_data(repository, page_rst_entry):

    return repository[page_rst_entry.sha]


def load_page_attachments(repository, page_tree):

    def load_page_attachment(attachment_tree):

        data = next(
            i for i in six.iteritems(attachment_tree)
            if i.path == ATTACHMENT_DATA
        )
        metadata_rst = next(
            i for i in six.iteritems(attachment_tree)
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

        return attachment_tree.id, data_blob_id, metadata_blob_id, data_callable, metadata_callable

    attachments = next(
        (i for i in six.iteritems(page_tree) if i.path == ATTACHMENTS_TREE),
        None,
    )

    if attachments is None:
        return []

    page_attachments_tree = repository[attachments.sha]

    page_attachment_trees = (
        repository[t.sha] for t in six.iteritems(page_attachments_tree)
    )

    return (load_page_attachment(t) for t in page_attachment_trees)
