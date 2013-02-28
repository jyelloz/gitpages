# -*- coding: utf-8 -*-

from flask import Blueprint, g
from datetime import datetime

from . import api, schema


def create_blueprint():

    from dulwich.repo import Repo
    from whoosh import index

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
            'ref': u'master',
        },
    )

    repo = Repo('repo.git')

    @gitpages_web_ui.before_request
    def setup_gitpages():
        g.gitpages = api.GitPages(repo, None, None)

    @gitpages_web_ui.teardown_request
    def teardown_gitpages(exception=None):

        gitpages = getattr(g, 'gitpages', None)

        if not gitpages:
            return

        gitpages.teardown()

    return gitpages_web_ui


def page_archive_view(year, month, day, slug, ref):

    page = g.gitpages.page(datetime(year, month, day), slug, ref)

    return page_view(page)


def page_view(page):

    from yaml import dump
    from pygments import highlight
    from pygments.lexers import YamlLexer
    from flask import render_template_string

    page_yaml = dump(page)

    page_html = highlight(page_yaml, YamlLexer(), _HTML_FORMATTER)

    html = render_template_string(
        _PAGE_TEMPLATE,
        title='Page#%s,%s' % (page.slug, page.ref),
        style_css=_STYLE_CSS,
        code_html=page_html,
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
        <div>
            <code>{{ code_html }}</code>
        </div>
    </body>
</html>
'''


def _build_html_formatter():
    from pygments.formatters import HtmlFormatter
    html_formatter = HtmlFormatter(style='monokai')
    style_css = html_formatter.get_style_defs('.highlight')

    return html_formatter, style_css

_HTML_FORMATTER, _STYLE_CSS = _build_html_formatter()
