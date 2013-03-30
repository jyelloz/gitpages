from flask import current_app
from flask.ext.script import Command

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
