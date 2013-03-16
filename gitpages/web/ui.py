# -*- coding: utf-8 -*-

import logging
from datetime import datetime
from urlparse import urljoin

from flask import (
    Blueprint, current_app, g, render_template, request, redirect, url_for
)
from werkzeug.exceptions import NotFound
from werkzeug.contrib.atom import AtomFeed

from .exceptions import PageNotFound
from .schema import ByDate, RevisionHistory
from .api import GitPages
from ..indexer import build_date_index, build_page_history_index


_log = logging.getLogger(__name__)


def create_blueprint():

    from whoosh import index
    from whoosh.query import Every

    gitpages_web_ui = Blueprint(
        'gitpages_web_ui',
        __name__,
        template_folder='templates',
    )

    gitpages_web_ui.add_url_rule(
        '/',
        'index_view',
        index_view_default_ref,
        defaults={
            'page_number': 1,
        },
    )

    gitpages_web_ui.add_url_rule(
        '/feed/atom',
        'atom_feed',
        atom_feed,
    )
    gitpages_web_ui.add_url_rule(
        '/feed/rss',
        'rss_feed_redirect',
        rss_feed_redirect,
    )

    gitpages_web_ui.add_url_rule(
        '/' + '/'.join(
            [
                'archives',
                '<int(fixed_digits=4):year>',
                '<int(fixed_digits=2):month>',
                '<int(fixed_digits=2):day>',
                '<slug>!<git_ref:ref>',
            ]
        ),
        'page_archive_view',
        page_archive_view,
    )
    gitpages_web_ui.add_url_rule(
        '/' + '/'.join(
            [
                'archives',
                '<int(fixed_digits=4):year>',
                '<int(fixed_digits=2):month>',
                '<int(fixed_digits=2):day>',
                '<slug>',
            ]
        ) + '/',
        'page_archive_view',
        page_archive_view_default_ref,
    )

    def get_index(index_path, index_name, schema):

        from os import makedirs
        from os.path import isdir

        try:
            makedirs(index_path)
        except:
            if not isdir(index_path):
                raise

        if index.exists_in(index_path, index_name):
            return index.open_dir(
                index_path,
                indexname=index_name,
            )

        return index.create_in(
            index_path,
            schema=schema,
            indexname=index_name,
        )

    @gitpages_web_ui.before_app_first_request
    def setup_gitpages_application():

        _log.debug('setting up blueprint')

        config = current_app.config

        repo = config['GITPAGES_REPOSITORY']
        ref = config['GITPAGES_DEFAULT_REF']

        date_index = get_index(
            config['GITPAGES_DATE_INDEX_PATH'],
            'date_index',
            ByDate(),
        )
        history_index = get_index(
            config['GITPAGES_HISTORY_INDEX_PATH'],
            'history_index',
            RevisionHistory(),
        )

        date_index.delete_by_query(Every())
        history_index.delete_by_query(Every())

        build_date_index(date_index, repo, ref)
        build_page_history_index(history_index, repo, ref)

        current_app.repo = repo
        current_app.default_ref = ref
        current_app.allowed_statuses = config['GITPAGES_ALLOWED_STATUSES']
        current_app.timezone = config['TIMEZONE']
        current_app.date_index = date_index
        current_app.history_index = history_index

    @gitpages_web_ui.before_request
    def setup_gitpages():
        g.timezone = current_app.timezone
        g.utcnow = datetime.utcnow()
        g.date_searcher = current_app.date_index.searcher()
        g.history_searcher = current_app.history_index.searcher()
        g.gitpages = GitPages(
            current_app.repo,
            g.date_searcher,
            g.history_searcher
        )
        g.allowed_statuses = current_app.allowed_statuses

    @gitpages_web_ui.teardown_request
    def teardown_gitpages(exception=None):

        gitpages = getattr(g, 'gitpages', None)
        date_searcher = getattr(g, 'date_searcher', None)
        history_searcher = getattr(g, 'history_searcher', None)

        if gitpages is not None:
            gitpages.teardown()

        if date_searcher is not None:
            date_searcher.close()

        if history_searcher is not None:
            history_searcher.close()

    return gitpages_web_ui


def index_view_default_ref(page_number):

    return index_view(page_number, current_app.default_ref)


def index_view(page_number, ref):

    results = g.gitpages.index(page_number, ref, statuses=g.allowed_statuses)

    html = render_template(
        'index.html',
        index=results,
    )

    return (
        html,
        200,
        {
            'Content-Type': 'text/html; charset=utf-8',
        },
    )


def page_archive_view_default_ref(year, month, day, slug):

    return page_archive_view(year, month, day, current_app.default_ref)


def page_archive_view(year, month, day, slug, ref):

    try:

        date = g.timezone.localize(datetime(year, month, day))
        page = g.gitpages.page(date, slug, ref, statuses=g.allowed_statuses)
        return page_view(page)

    except PageNotFound:
        raise NotFound()


def atom_feed():

    config = current_app.config

    feed = AtomFeed(
        config['SITE_TITLE'],
        feed_url=request.url,
        url=request.url_root,
    )

    results = g.gitpages.index(
        1,
        ref=config['GITPAGES_DEFAULT_REF'],
        statuses=g.allowed_statuses,
    )

    for page in results:

        doc = page.doc()

        feed.add(
            doc['title'],
            doc['body'],
            content_type='html',
            url=urljoin(request.url_root, page.to_url()),
            updated=page.info.date,
            published=page.info.date,
        )

    return feed.get_response()


def rss_feed_redirect():
    return redirect(url_for('.atom_feed'), code=301)


def page_to_key(page):
    return page.info.blob_id


def page_view(page):

    doc = page.doc()
    older = g.gitpages.older_pages(
        page,
        ref=page.info.ref,
        page_number=1,
        page_length=1,
        statuses=g.allowed_statuses,
    )
    newer = g.gitpages.newer_pages(
        page,
        ref=page.info.ref,
        page_number=1,
        page_length=1,
        statuses=g.allowed_statuses,
    )

    history = g.gitpages.history(
        page,
        ref=page.info.ref,
        page_number=1,
    )

    body = doc['body']
    title = doc['title']

    html = render_template(
        'page.html',
        title=title,
        body=body,
        page=page,
        page_prev=next(iter(older), None),
        page_next=next(iter(newer), None),
        page_history=history,
    )

    return (
        html,
        200,
        {
            'Content-Type': 'text/html; charset=utf-8',
        },
    )
