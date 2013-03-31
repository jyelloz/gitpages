# -*- coding: utf-8 -*-

import itertools
import functools
import posixpath

PAGES_TREE, = 'page',


def iterable_nth(iterable, n, default=None):
    return next(itertools.islice(iterable, n, None), default)


def get_pages_tree(repository, ref='HEAD', commit=None):

    if commit is None:
        ref_commit = repository.commit(repository.refs[ref])
        root = repository.tree(ref_commit.tree)
    else:
        root = repository.tree(commit.tree)

    return repository.tree(root['page'][1])


def find_pages(repository, pages_tree, prefix=PAGES_TREE):

    page_entries = pages_tree.iteritems()

    page_trees = ((e.path, repository.tree(e.sha)) for e in page_entries)

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
        i for i in page_tree.iteritems()
        if i.path == 'page.rst'
    )


def load_page_data(repository, page_rst_entry):

    return repository.get_blob(page_rst_entry.sha)


def load_page_attachments(repository, page_tree):

    def load_page_attachment(attachment_tree):

        metadata_rst = next(
            i for i in attachment_tree.iteritems()
            if i.path == 'metadata.rst'
        )
        data = next(
            i for i in attachment_tree.iteritems()
            if i.path == 'data'
        )

        metadata = repository.get_blob(metadata_rst.sha).data
        data_callable = functools.partial(repository.get_blob, data.sha)

        return metadata, data_callable

    attachments = next(
        (i for i in page_tree.iteritems() if i.path == 'attachment'), None
    )

    if attachments is None:
        return []

    page_attachments_tree = repository.tree(attachments.sha)

    page_attachment_trees = (
        repository.tree(t.sha) for t in page_attachments_tree.iteritems()
    )

    return (load_page_attachment(t) for t in page_attachment_trees)
