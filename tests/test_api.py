# -*- coding: utf-8 -*-

from unittest import TestCase

from nose.tools import raises

from dulwich.repo import MemoryRepo
from dulwich.objects import Blob, Commit, Tree

from whoosh.filedb.filestore import RamStorage

from gitpages.indexer import build_hybrid_index
from gitpages.web.api import GitPages
from gitpages.web.schema import DateRevisionHybrid
from gitpages.web.exceptions import PageNotFound, AttachmentNotFound


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


class APITestCase(TestCase):

    def setUp(self):

        self.tearDown()

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

    def tearDown(self):

        searcher = getattr(self, 'searcher', None)
        index = getattr(self, 'index', None)

        if searcher is not None:
            searcher.close()

        if index is not None:
            index.close()

    def test_page_by_path(self):

        sample_page = self.api.page_by_path('page/sample-page/page.rst')
        self.assertTrue(sample_page)

    @raises(PageNotFound)
    def test_page_by_path_not_found(self):

        self.api.page_by_path('page/non-existent-page/page.rst')

    def test_attachments_by_path(self):

        path = 'page/sample-page-with-attachments/page.rst'

        attachments = list(self.api.attachments_by_path(path))

        for attachment in attachments:
            print attachment

    def test_attachments_by_path_empty(self):

        path = 'page/sample-page/page.rst'

        self.api.page_by_path(path)
        attachments = list(self.api.attachments_by_path(path))

        self.assertEqual(len(attachments), 0)

    @raises(AttachmentNotFound)
    def test_attachment_not_found(self):

        fake_tree_id = '1' * 40

        self.api.attachment(fake_tree_id)

    def test_index(self):

        pages, results = self.api.index(1, 'HEAD')

        pages_list = list(pages)
        page, page_with_attachments = pages_list

        self.assertEqual(len(pages_list), 2)
        self.assertEqual(page.info.title, u'Sample Page With Attachments')
        self.assertEqual(page_with_attachments.info.title, u'Sample Page')
