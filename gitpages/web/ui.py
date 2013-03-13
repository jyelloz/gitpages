# -*- coding: utf-8 -*-

from datetime import datetime

from flask import Blueprint, g
from werkzeug.exceptions import NotFound
from pytz import timezone

from .exceptions import PageNotFound
from .schema import ByDate, PageHistory
from .api import GitPages
from ..indexer import build_date_index


def create_blueprint(config):

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
        index_view,
        defaults={
            'page_number': 1,
            'ref': u'refs/heads/realposts',
        },
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
        page_archive_view
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
        page_archive_view,
        defaults={
            'ref': u'refs/heads/realposts',
        },
    )

    repo = config['GITPAGES_REPOSITORY']

    def get_index(index_path, index_name, schema):

        try:
            from os import makedirs
            makedirs(index_path)
        except:
            from os.path import isdir
            if not (isdir(index_path)):
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

    date_index = get_index(
        config['GITPAGES_DATE_INDEX_PATH'],
        'date_index',
        ByDate(),
    )
    history_index = get_index(
        config['GITPAGES_HISTORY_INDEX_PATH'],
        'history_index',
        PageHistory(),
    )

    date_index.delete_by_query(Every())
    build_date_index(date_index, repo, 'refs/heads/realposts')

    los_angeles_tz = timezone('America/Los_Angeles')

    @gitpages_web_ui.before_request
    def setup_gitpages():
        g.timezone = los_angeles_tz
        g.utcnow = datetime.utcnow()
        g.date_searcher = date_index.searcher()
        g.history_searcher = history_index.searcher()
        g.gitpages = GitPages(repo, g.date_searcher, g.history_searcher)

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


def index_view(page_number, ref):

    from flask import render_template

    results = g.gitpages.index(page_number, ref)

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


def page_archive_view(year, month, day, slug, ref):

    try:

        date = g.timezone.localize(datetime(year, month, day))
        page = g.gitpages.page(date, slug, ref)
        return page_view(page)

    except PageNotFound:
        raise NotFound()


def page_to_key(page):
    return page.info.blob_id


def page_view(page):

    from flask import render_template

    doc = page.doc()
    older = g.gitpages.older_pages(
        page,
        ref=page.info.ref,
        page_number=1,
        page_length=1,
    )
    newer = g.gitpages.newer_pages(
        page,
        ref=page.info.ref,
        page_number=1,
        page_length=1,
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
    )

    return (
        html,
        200,
        {
            'Content-Type': 'text/html; charset=utf-8',
        },
    )
