# -*- coding: utf-8 -*-

import unittest

from dulwich.repo import MemoryRepo
from dulwich.objects import Blob, Commit, Tree

from whoosh.filedb.filestore import RamStorage

from gitpages.indexer import build_hybrid_index
from gitpages.web.api import GitPages
from gitpages.web.schema import DateRevisionHybrid


_SAMPLE_PAGE_RST = b"""\
Sample Page
===========

:Author: Fake Fakesworthy
:date: 2011-11-11 11:11:11-08:00
:status: published

:date created: 2011-11-11 11:11:11-08:00
:date modified: 2011-11-11 11:11:11-08:00

This is a sample page.

Here is some ``inline literal text``.
Here is some :strikethrough:`strikethrough text`.

"""

_SAMPLE_PAGE_WITH_ATTACHMENTS_RST = b"""\
Sample Page With Attachments
============================

:Author: Fake Fakesworthy
:date: 2012-12-12 12:12:12-08:00
:status: published

:date created: 2012-12-12 12:12:12-08:00
:date modified: 2012-12-12 12:12:12-08:00

This is a sample page with some attachments.
"""

_ATTACH_1 = b'attach.1'
_ATTACH_1_DATA = b'attach.1 data\n'
_ATTACH_1_METADATA_RST = b"""\
:content-disposition: attachment; filename=%s
:content-type: text/plain
""" % _ATTACH_1

_PAGE_RST = b'page.rst'
_METADATA_RST = b'metadata.rst'
_DATA = b'data'


def _add_attachment(store, attachments_tree, filename, metadata, data):

    metadata_blob = Blob.from_string(metadata)
    data_blob = Blob.from_string(data)

    store.add_object(metadata_blob)
    store.add_object(data_blob)

    attachment_tree = Tree()
    attachment_tree.add(
        _METADATA_RST,
        0o100644,
        metadata_blob.id,
    )
    attachment_tree.add(
        _DATA,
        0o100644,
        data_blob.id,
    )
    store.add_object(attachment_tree)

    attachments_tree.add(
        filename,
        0o100755,
        attachment_tree.id,
    )
    return attachments_tree


class GitPagesTestcase(unittest.TestCase):

    def setUp(self):
        self.setup()

    def tearDown(self):
        self.teardown()

    def assert_equal(self, x, y):
        self.assertEqual(x, y)

    def assert_true(self, x):
        self.assertTrue(x)

    def setup(self):

        self.teardown()

        index = RamStorage().create_index(DateRevisionHybrid())

        repo = MemoryRepo()
        store = repo.object_store

        sample_page_rst_blob, sample_page_with_attachments_rst_blob = (
            Blob.from_string(_SAMPLE_PAGE_RST),
            Blob.from_string(_SAMPLE_PAGE_WITH_ATTACHMENTS_RST),
        )

        store.add_object(sample_page_rst_blob)
        store.add_object(sample_page_with_attachments_rst_blob)

        sample_page_tree = Tree()
        sample_page_tree.add(_PAGE_RST, 0o100644, sample_page_rst_blob.id)
        store.add_object(sample_page_tree)

        attach_tree = Tree()
        _add_attachment(
            store,
            attach_tree,
            _ATTACH_1,
            _ATTACH_1_METADATA_RST,
            _ATTACH_1_DATA
        )
        store.add_object(attach_tree)

        sample_page_with_attachments_tree = Tree()
        sample_page_with_attachments_tree.add(
            _PAGE_RST, 0o100644, sample_page_with_attachments_rst_blob.id
        )
        sample_page_with_attachments_tree.add(
            b'attachment', 0o100755, attach_tree.id
        )
        store.add_object(sample_page_with_attachments_tree)

        pages_tree = Tree()
        pages_tree.add(b'sample-page', 0o100755, sample_page_tree.id)
        pages_tree.add(
            b'sample-page-with-attachments',
            0o100755,
            sample_page_with_attachments_tree.id,
        )
        store.add_object(pages_tree)

        root_tree = Tree()
        root_tree.add(b'page', 0o100755, pages_tree.id)
        store.add_object(root_tree)

        c = Commit()
        c.tree = root_tree.id
        c.message = b'initial commit'
        c.committer = b'test committer <test@committer>'
        c.author = b'test author <test@author>'
        c.commit_time = 1174773719
        c.author_time = 1174773719
        c.commit_timezone = 0
        c.author_timezone = 0

        store.add_object(c)

        repo.refs[b'refs/heads/master'] = c.id
        repo.refs[b'HEAD'] = c.id

        build_hybrid_index(
            index=index,
            repo=repo,
            ref=b'HEAD',
        )

        searcher = index.searcher()

        self.index = index
        self.searcher = searcher
        self.api = GitPages(repo, searcher)

        self.repo = repo
        self.root_tree = root_tree
        self.pages_tree = pages_tree
        self.sample_page_tree = sample_page_tree
        self.sample_page_rst_blob = sample_page_rst_blob

    def teardown(self):

        searcher = getattr(self, 'searcher', None)
        index = getattr(self, 'index', None)

        if searcher is not None:
            searcher.close()

        if index is not None:
            index.close()
