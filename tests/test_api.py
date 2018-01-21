# -*- coding: utf-8 -*-

from pytest import raises

from gitpages.web.exceptions import PageNotFound, AttachmentNotFound

from .base import GitPagesTestcase, _ATTACH_1
from gitpages.util.compat import _text_to_bytes

from datetime import date


class APITestCase(GitPagesTestcase):

    PAGE = u'sample-page'
    PAGE_PATH = u'page/{}/page.rst'.format(PAGE)
    PAGE_WITH_ATTACHMENTS = u'sample-page-with-attachments'
    PAGE_WITH_ATTACHMENTS_PATH = u'page/{}/page.rst'.format(
        PAGE_WITH_ATTACHMENTS
    )

    def test_when__page__hasnoattachments__then_attachments__isempty(self):

        attachments = self.api.attachments(
            date(2012, 11, 11),
            self.PAGE,
        )

        assert not attachments

    def test_when__page__hasattachments__then_attachments__isnotempty(self):

        attachments = self.api.attachments(
            date(2012, 12, 12),
            self.PAGE_WITH_ATTACHMENTS,
        )

        a = next(attachments)

        self.assert_equal(
            _text_to_bytes(a.filename),
            _ATTACH_1,
        )

    def test_page_by_path(self):

        sample_page = self.api.page_by_path(self.PAGE_PATH)
        self.assert_true(sample_page)

    def test_page_by_path_not_found(self):
        with raises(PageNotFound):
            self.api.page_by_path('page/non-existent-page/page.rst')

    def test_attachments_by_path(self):

        attachments = self.api.attachments_by_path(
            self.PAGE_WITH_ATTACHMENTS_PATH
        )

        a = next(attachments)

        self.assert_equal(
            _text_to_bytes(a.filename),
            _ATTACH_1,
        )

    def test_attachments_by_path_empty(self):

        attachments = list(self.api.attachments_by_path(self.PAGE_PATH))

        self.assert_equal([], attachments)

    def test_attachment_not_found(self):

        fake_tree_id = b'1' * 40

        with raises(AttachmentNotFound):
            self.api.attachment(fake_tree_id)

    def test_index(self):

        pages, results = self.api.index(1, 'HEAD')

        pages_list = list(pages)
        page, page_with_attachments = pages_list

        self.assert_equal(len(pages_list), 2)
        self.assert_equal(page.info.title, u'Sample Page With Attachments')
        self.assert_equal(page_with_attachments.info.title, u'Sample Page')
