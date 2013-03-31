from flask import current_app
from flask.ext.script import Command, Option

from .web import ui

from .indexer import build_hybrid_index


class BuildIndex(Command):
    '(re)builds GitPages index'

    def handle(self, app, *args, **kwargs):

        with app.test_request_context():
            ui.setup_gitpages_application()
            ui.setup_gitpages()
            return self.run(*args, **kwargs)

    def run(self):

        from whoosh.query import Every

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
