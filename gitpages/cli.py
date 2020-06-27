import click

from functools import partial

from whoosh.query import Every


@click.command('build-index')
@click.pass_obj
def build_index(app):
    """(re)build GitPages index"""

    from .indexer import build_hybrid_index
    from .web import ui

    with app.test_request_context():

        ui.setup_gitpages_application()
        ui.setup_gitpages()

        index = app.index

        index.delete_by_query(Every())

        build_hybrid_index(
            index=index,
            repo=app.repo,
            ref=app.default_ref,
        )


@click.command('run-server')
@click.option(
    '-p', '--port',
    envvar='GITPAGES_PORT', metavar='<PORT>',
    default=5000,
    help='Listen on <PORT>',
)
@click.option(
    '-H', '--host',
    envvar='GITPAGES_HOST', metavar='<IP>',
    default='127.0.0.1',
    help='Bind to address <IP>',
)
@click.option(
    '--debug/--no-debug',
    envvar='GITPAGES_DEBUG',
    default=True,
    help='Enable debugging and autoreloading',
)
@click.pass_obj
def run_server(app, host, port, debug):
    """ run a local webserver """

    app.run(port=port, host=host, debug=debug)


@click.command('shell')
@click.argument(
    'shell', metavar='[SHELL]',
    type=click.Choice(['ptpython', 'python']),
    default='ptpython',
)
@click.pass_obj
def shell(app, shell):
    """ run an interactive python shell """

    from flask import request, session, g, url_for
    from .web import ui

    shells = {
        'ptpython': _ptpython,
        'python': _python,
    }

    context = dict(
        app=app,
        request=request,
        session=session,
        g=g,
        url_for=url_for,
    )

    with app.test_request_context():
        ui.setup_gitpages_application()
        ui.setup_gitpages()
        shells[shell](None, context)()


def _ptpython(banner, context):

    from ptpython.repl import embed

    return partial(
        embed,
        globals=dict(),
        locals=context,
    )


def _python(banner, context):

    from code import interact

    return partial(
        interact,
        banner,
        local=context,
    )
