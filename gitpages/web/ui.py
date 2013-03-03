# -*- coding: utf-8 -*-

from flask import Blueprint, g
from werkzeug.exceptions import NotFound
from datetime import datetime
from pytz import timezone

from .exceptions import PageNotFound
from .schema import ByDate, PageHistory
from .api import GitPages
from ..indexer import build_date_index


def create_blueprint():

    from dulwich.repo import Repo
    from whoosh import index
    from whoosh.query import Every

    gitpages_web_ui = Blueprint('gitpages_web_ui', __name__)

    gitpages_web_ui.add_url_rule(
        '/' + '/'.join(
            [
                'page',
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
                'page',
                '<int(fixed_digits=4):year>',
                '<int(fixed_digits=2):month>',
                '<int(fixed_digits=2):day>',
                '<slug>',
            ]
        ),
        'page_archive_view',
        page_archive_view,
        defaults={
            'ref': u'refs/heads/realposts',
        },
    )

    repo = Repo('database')

    index_dir = 'index'
    try:
        from os import makedirs
        makedirs(index_dir)
    except:
        from os.path import isdir

        if not isdir(index_dir):
            raise

    bydate_schema = ByDate()
    pagehistory_schema = PageHistory()

    if index.exists_in(index_dir, 'by_date'):
        date_index = index.open_dir(
            index_dir,
            indexname='by_date',
        )
    else:
        date_index = index.create_in(
            index_dir,
            schema=bydate_schema,
            indexname='by_date',
        )

    if index.exists_in(index_dir, 'page_history'):
        history_index = index.open_dir(
            index_dir,
            indexname='page_history',
        )
    else:
        history_index = index.create_in(
            index_dir,
            schema=pagehistory_schema,
            indexname='page_history',
        )

    date_index.delete_by_query(Every())
    build_date_index(date_index, repo, 'refs/heads/realposts')

    los_angeles_tz = timezone('America/Los_Angeles')

    @gitpages_web_ui.before_request
    def setup_gitpages():
        g.timezone = los_angeles_tz
        g.gitpages = GitPages(repo, date_index, history_index)

    @gitpages_web_ui.teardown_request
    def teardown_gitpages(exception=None):

        gitpages = getattr(g, 'gitpages', None)

        if not gitpages:
            return

        gitpages.teardown()

    return gitpages_web_ui


def page_archive_view(year, month, day, slug, ref):

    try:

        date = g.timezone.localize(datetime(year, month, day))
        page = g.gitpages.page(date, slug, ref)
        return page_view(page)

    except PageNotFound:
        raise NotFound()


def page_view(page):

    from flask import render_template_string

    doc = page.doc()
    html_body = doc['html_body']
    title = doc['title']

    html = render_template_string(
        _PAGE_TEMPLATE,
        title=title,
        style_css=_STYLE_CSS,
        html_body=html_body,
    )

    return (
        html,
        200,
        {
            'Content-Type': 'text/html; charset=utf-8',
        },
    )

_PAGE_TEMPLATE = u'''\
<!DOCTYPE html>
<html>
    <head>
        <meta http-equiv="Content-Type" content="text/html; charset=utf-8" />
        <title>{{ title }}</title>
        <style type="text/css">
        {{ style_css }}
        </style>
    </head>
    <body class="highlight">
        {{ html_body }}
    </body>
</html>
'''


def _build_html_formatter():
    from pygments.formatters import HtmlFormatter
    html_formatter = HtmlFormatter(style='monokai')
    style_css = html_formatter.get_style_defs('.highlight')

    return html_formatter, style_css

_HTML_FORMATTER, _STYLE_CSS = _build_html_formatter()
