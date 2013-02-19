from flask import Flask, Blueprint, g
from flask_failsafe import failsafe

import api as web_api


@failsafe
def create():

    from dulwich.repo import Repo

    gitpages_web_ui = Blueprint('gitpages_web_ui', __name__)

    gitpages_web_ui.add_url_rule('/page/<page_pk>', 'page_view', page_view)
    gitpages_web_ui.gitpages = web_api.GitPages(None, None)

    repo = Repo('repo.git')

    @gitpages_web_ui.before_request
    def setup_gitpages():
        g.gitpages = web_api.GitPages(repo, None)

    @gitpages_web_ui.teardown_request
    def teardown_gitpages(exception=None):

        gitpages = getattr(g, 'gitpages', None)

        if not gitpages:
            return

        gitpages.teardown()

    application = Flask(__name__)
    application.register_blueprint(gitpages_web_ui)

    return application


def page_view(page_pk):

    from yaml import dump
    from pygments import highlight
    from pygments.lexers import YamlLexer
    from flask import render_template_string

    page = web_api.page(page_pk)
    page_yaml = dump(page)

    page_html = highlight(page_yaml, YamlLexer(), _HTML_FORMATTER)

    html = render_template_string(
        _PAGE_TEMPLATE,
        title='Page#%s' % page_pk,
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


if __name__ == '__main__':
    create().run(debug=True)
