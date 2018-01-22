# -*- coding: utf-8 -*-

import functools
import posixpath
from collections import namedtuple

import six

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


PageRef = namedtuple(
    'PageRef',
    [
        'path',
        'tree',
        'entry',
    ],
)


_PageBase = namedtuple(
    'Page',
    [
        'path',
        'page',
        'attachments',
    ],
)


class Page(_PageBase):

    @property
    def attachments(self):
        '''
        :return: iterable(PageAttachment)
        '''
        return super(Page, self).attachments


_PageAttachmentBase = namedtuple(
    'PageAttachment',
    [
        'tree_id',
        'blob_id',
        'metadata_blob_id',
        'data',
        'metadata',
    ],
)

class PageAttachment(_PageAttachmentBase):

    @property
    def tree_id_text(self):
        return _from_bytes(self.tree_id)

    @property
    def blob_id_text(self):
        return _from_bytes(self.blob_id)

    @property
    def metadata_blob_id_text(self):
        return _from_bytes(self.metadata_blob_id)

    @property
    def data(self):
        return super(PageAttachment, self).data()

    @property
    def metadata(self):
        return super(PageAttachment, self).metadata()


def get_pages_tree(repository, ref=b'HEAD'):
    """
    :type repository: dulwich.repo.BaseRepo
    :rtype: dulwich.objects.Tree
    """

    ref_commit = repository[repository.refs[ref]]
    root = repository[ref_commit.tree]

    return repository[root[PAGES_TREE_BYTES][1]]


def find_pages(repository, pages_tree, prefix=PAGES_TREE):
    """
    :rtype: list(PageRef)
    """

    page_entries = six.iteritems(pages_tree)

    page_trees = (
        (_from_bytes(e.path), repository[e.sha])
        for e in page_entries
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


def load_pages_with_attachments(repository, page_trees_with_rst):
    """
    :type repository: dulwich.repo.BaseRepo
    :rtype: list(Page)
    """

    return (
        Page(
            path,
            load_page_data(repository, page_rst_entry),
            load_page_attachments(repository, page_tree),
        )
        for (path, page_tree, page_rst_entry) in page_trees_with_rst
    )


def find_page_rst_entry(page_tree):
    """
    :type page_tree: dulwich.objects.Tree
    :rtype: dulwich.objects.TreeEntry
    """

    return next(
        i for i in six.iteritems(page_tree)
        if _from_bytes(i.path) == PAGE_RST
    )


def load_page_data(repository, page_rst_entry):
    """
    :type repository: dulwich.repo.BaseRepo
    :type page_rst_entry: dulwich.objects.TreeEntry
    :rtype: dulwich.objects.Blob
    """

    return repository[page_rst_entry.sha]


def load_page_attachments(repository, page_tree):
    """
    :type repository: dulwich.repo.BaseRepo
    :type page_tree: dulwich.objects.Tree
    :rtype: iterable(PageAttachment)
    """

    def load_page_attachment(attachment_tree):
        """
        :type attachment_tree: dulwich.objects.Tree
        :rtype: PageAttachment
        """

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

        return PageAttachment(
            attachment_tree.id,
            data_blob_id,
            metadata_blob_id,
            data_callable,
            metadata_callable,
        )

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
