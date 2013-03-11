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

    date_index_path = config['GITPAGES_DATE_INDEX_PATH']
    history_index_path = config['GITPAGES_HISTORY_INDEX_PATH']
    try:
        from os import makedirs
        makedirs(date_index_path)
        makedirs(history_index_path)
    except:
        from os.path import isdir

        if not (isdir(date_index_path) and isdir(history_index_path)):
            raise

    bydate_schema = ByDate()
    pagehistory_schema = PageHistory()

    if index.exists_in(date_index_path, 'by_date'):
        date_index = index.open_dir(
            date_index_path,
            indexname='by_date',
        )
    else:
        date_index = index.create_in(
            date_index_path,
            schema=bydate_schema,
            indexname='by_date',
        )

    if index.exists_in(history_index_path, 'page_history'):
        history_index = index.open_dir(
            history_index_path,
            indexname='page_history',
        )
    else:
        history_index = index.create_in(
            history_index_path,
            schema=pagehistory_schema,
            indexname='page_history',
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

    title = 'Index'

    html = render_template(
        'index.html',
        title=title,
        index=results,
        style_css=_STYLE_CSS,
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
        style_css=_STYLE_CSS,
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


def _build_html_formatter():

    from pygments.formatters import HtmlFormatter

    html_formatter = HtmlFormatter(style='bw')
    style_css = html_formatter.get_style_defs('.code')

    return html_formatter, style_css

_HTML_FORMATTER, _STYLE_CSS = _build_html_formatter()
