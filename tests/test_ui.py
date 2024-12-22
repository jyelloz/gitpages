# -*- coding: utf-8 -*-

import cachelib
from datetime import UTC

from gitpages.web.application import create

from .base import GitPagesTestcase


class UITest(GitPagesTestcase):

    def setup(self):

        super(UITest, self).setup()

        def get_ram_index(*args, **kwargs):
            return self.index

        app = create()
        app.testing = True

        app.config.update(
            TIMEZONE=UTC,
            SITE_TITLE=u'GitPages',
            GITPAGES_REPOSITORY=self.repo,
            GITPAGES_DEFAULT_REF='refs/heads/master',
            GITPAGES_ALLOWED_STATUSES=[u'published', u'draft'],
            GITPAGES_INDEX=get_ram_index,
            CACHE=cachelib.NullCache(),
            DEBUG=True,
        )

        self.app = app

    def teardown(self):
        pass

    def test_page_not_found(self):

        with self.app.test_client() as ctx:

            response = ctx.get('/archives/1111/11/11/non-existent-page/')
            self.assert_equal(response.status_code, 404)

    def test_page_found(self):

        with self.app.test_client() as ctx:

            response = ctx.get('/archives/2011/11/11/sample-page/')
            self.assert_equal(response.status_code, 200)
