from functools import partial

from flask import current_app
from flask_script import Command, Option, Shell as _Shell

from .web import ui

from .indexer import build_hybrid_index


class BuildIndex(Command):
    '(re)builds GitPages index'

    def run(self):

        from whoosh.query import Every

        ui.setup_gitpages_application()
        ui.setup_gitpages()

        index = current_app.index

        index.delete_by_query(Every())

        build_hybrid_index(
            index=index,
            repo=current_app.repo,
            ref=current_app.default_ref,
        )


class GunicornServer(Command):

    description = 'Run the app within Gunicorn'

    def __init__(self, host='127.0.0.1', port=8000, workers=4):
        self.port = port
        self.host = host
        self.workers = workers

    def get_options(self):
        return (
            Option('-H', '--host',
                   dest='host',
                   default=self.host),

            Option('-p', '--port',
                   dest='port',
                   type=int,
                   default=self.port),

            Option('-w', '--workers',
                   dest='workers',
                   type=int,
                   default=self.workers),
        )

    def handle(self, app, host, port, workers):

        from gunicorn.app.base import Application

        class FlaskApplication(Application):

            def init(self, parser, opts, args):
                return dict(
                    bind='{0}:{1}'.format(host, port),
                    workers=workers,
                    proc_name=app.config['SITE_TITLE'],
                    preload_app=True,
                )

            def load(self):
                return app

        FlaskApplication().run()


class Shell(_Shell):

    def run(self, no_ipython, no_bpython):
        '''A better version of run()'''

        banner = self.banner
        context = self.get_context()

        def shells():

            if not no_ipython:
                yield self._ipython(banner, context)

            if not no_bpython:
                yield self._bpython(banner, context)

            yield self._python(banner, context)

        for shell in shells():
            try:
                shell()
                return
            except:
                continue

    @staticmethod
    def _ipython(banner, context):

        try:

            from IPython.Shell import IPShellEmbed

            return partial(
                IPShellEmbed(banner=banner),
                global_ns=dict(),
                local_ns=context,
            )

        except ImportError:

            from IPython.terminal.embed import InteractiveShellEmbed

            return partial(
                InteractiveShellEmbed(banner1=banner),
                global_ns=dict(),
                local_ns=context,
            )

    @staticmethod
    def _bpython_urwid(banner, context):

        from bpython.urwid import main

        return partial(
            main,
            banner=banner,
            locals_=context,
        )

    @staticmethod
    def _bpython(banner, context):

        from bpython import embed

        return partial(
            embed,
            banner=banner,
            locals_=context,
        )

    @staticmethod
    def _python(banner, context):

        from code import interact

        return partial(
            interact,
            banner,
            local=context,
        )
