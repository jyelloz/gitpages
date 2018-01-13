# -*- coding: utf-8 -*-

import unittest

from dulwich.repo import MemoryRepo
from dulwich.objects import Blob, Commit, Tree

from whoosh.filedb.filestore import RamStorage

from gitpages.indexer import build_hybrid_index
from gitpages.web.api import GitPages
from gitpages.web.schema import DateRevisionHybrid


_SAMPLE_PAGE_RST = """\
Sample Page
===========

:Author: Fake Fakesworthy
:date: 2011-11-11 11:11:11-08:00
:status: published

:date created: 2011-11-11 11:11:11-08:00
:date modified: 2011-11-11 11:11:11-08:00

This is a sample page.

Here is some ``inline literal text``.

"""

_SAMPLE_PAGE_WITH_ATTACHMENTS_RST = """\
Sample Page With Attachments
============================

:Author: Fake Fakesworthy
:date: 2012-12-12 12:12:12-08:00
:status: published

:date created: 2012-12-12 12:12:12-08:00
:date modified: 2012-12-12 12:12:12-08:00

This is a sample page with some attachments.
"""


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
        sample_page_tree.add('page.rst', 0100644, sample_page_rst_blob.id)
        store.add_object(sample_page_tree)

        sample_page_with_attachments_tree = Tree()
        sample_page_with_attachments_tree.add(
            'page.rst', 0100644, sample_page_with_attachments_rst_blob.id
        )
        store.add_object(sample_page_with_attachments_tree)

        pages_tree = Tree()
        pages_tree.add('sample-page', 0100755, sample_page_tree.id)
        pages_tree.add(
            'sample-page-with-attachments',
            0100755,
            sample_page_with_attachments_tree.id,
        )
        store.add_object(pages_tree)

        root_tree = Tree()
        root_tree.add('page', 0100755, pages_tree.id)
        store.add_object(root_tree)

        c = Commit()
        c.tree = root_tree.id
        c.message = 'initial commit'
        c.committer = 'test committer <test@committer>'
        c.author = 'test author <test@author>'
        c.commit_time = 1174773719
        c.author_time = 1174773719
        c.commit_timezone = 0
        c.author_timezone = 0

        store.add_object(c)

        repo.refs['refs/heads/master'] = c.id
        repo.refs['HEAD'] = c.id

        build_hybrid_index(
            index=index,
            repo=repo,
            ref='HEAD',
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
