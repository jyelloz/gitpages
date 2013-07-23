# -*- coding: utf-8 -*-

from nose.tools import raises

from gitpages.web.exceptions import PageNotFound, AttachmentNotFound

from .base import GitPagesTestcase


class APITestCase(GitPagesTestcase):

    def test_page_by_path(self):

        sample_page = self.api.page_by_path('page/sample-page/page.rst')
        self.assert_true(sample_page)

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

        self.assert_equal(len(attachments), 0)

    @raises(AttachmentNotFound)
    def test_attachment_not_found(self):

        fake_tree_id = '1' * 40

        self.api.attachment(fake_tree_id)

    def test_index(self):

        pages, results = self.api.index(1, 'HEAD')

        pages_list = list(pages)
        page, page_with_attachments = pages_list

        self.assert_equal(len(pages_list), 2)
        self.assert_equal(page.info.title, u'Sample Page With Attachments')
        self.assert_equal(page_with_attachments.info.title, u'Sample Page')
