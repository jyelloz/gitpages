# -*- coding: utf-8 -*-

import itertools
import functools


def iterable_nth(iterable, n, default=None):
    return next(itertools.islice(iterable, n, None), default)


def get_pages_tree(repository, ref='HEAD'):

    commit = repository.commit(repository.refs[ref])

    root = repository.tree(commit.tree)

    return repository.tree(root['page'][1])


def find_pages(repository, pages_tree):

    page_items = pages_tree.iteritems()

    page_tree_shas = (entry.sha for entry in page_items)
    page_trees = (repository.tree(sha) for sha in page_tree_shas)

    return (load_page_data(repository, page_tree) for page_tree in page_trees)


def load_page_data(repository, page_tree):

    page_rst = [i for i in page_tree.iteritems() if i.path == 'page.rst'].pop()

    page_rst_blob = repository.get_blob(page_rst.sha)

    return page_rst_blob.data, load_page_attachments(repository, page_tree)


def load_page_attachments(repository, page_tree):

    def load_page_attachment(attachment_tree):

        metadata_rst = iterable_nth(
            (
                i for i in attachment_tree.iteritems()
                if i.path == 'metadata.rst'
            ),
            0,
        )
        data = iterable_nth(
            (
                i for i in attachment_tree.iteritems()
                if i.path == 'data'
            ),
            0,
        )

        metadata = repository.get_blob(metadata_rst.sha).data
        data_callable = functools.partial(repository.get_blob, data.sha)

        return metadata, data_callable

    attachments = iterable_nth(
        (
            i for i in page_tree.iteritems()
            if i.path == 'attachment'
        ),
        0,
    )

    if attachments is None:
        return []

    page_attachments_tree = repository.tree(attachments.sha)

    page_attachment_trees = (
        repository.tree(t.sha) for t in page_attachments_tree.iteritems()
    )

    return (load_page_attachment(t) for t in page_attachment_trees)
