# -*- coding: utf-8 -*-

from unittest import TestCase

from nose.tools import raises

from dulwich.repo import MemoryRepo
from dulwich.objects import Blob, Commit, Tree

from whoosh.filedb.filestore import RamStorage

from gitpages.indexer import build_hybrid_index
from gitpages.web.api import GitPages
from gitpages.web.schema import DateRevisionHybrid
from gitpages.web.exceptions import PageNotFound


_SAMPLE_PAGE_RST = """\
Sample Page
===========

:Author: Fake Fakesworthy
:date: 2011-11-11 11:11:11-08:00
:status: published

:date created: 2011-11-11 11:11:11-08:00
:date modified: 2011-11-11 11:11:11-08:00

This is a sample page.
"""


class APITestCase(TestCase):

    def setUp(self):

        self.tearDown()

        index = RamStorage().create_index(DateRevisionHybrid())

        repo = MemoryRepo()
        store = repo.object_store

        sample_page_rst_blob = Blob.from_string(_SAMPLE_PAGE_RST)
        store.add_object(sample_page_rst_blob)

        sample_page_tree = Tree()
        sample_page_tree.add('page.rst', 0100644, sample_page_rst_blob.id)
        store.add_object(sample_page_tree)

        pages_tree = Tree()
        pages_tree.add('sample-page', 0100755, sample_page_tree.id)
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

    def tearDown(self):

        searcher = getattr(self, 'searcher', None)
        index = getattr(self, 'index', None)

        if searcher is not None:
            searcher.close()

        if index is not None:
            index.close()

    def test_page_by_path_success(self):

        sample_page = self.api.page_by_path('page/sample-page/page.rst')
        self.assertTrue(sample_page)

    @raises(PageNotFound)
    def test_page_by_path_failure(self):

        sample_page = self.api.page_by_path('page/non-existent-page/page.rst')
        self.assertIsNotNone(sample_page)

    def test_index(self):

        pages, results = self.api.index(1, 'HEAD')

        pages_list = list(pages)
        page = pages_list[0]

        self.assertEqual(len(pages_list), 1)
        self.assertEqual(page.info.title, u'Sample Page')
