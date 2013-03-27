from flask import current_app
from flask.ext.script import Command

from .web import ui

from .indexer import build_date_index, build_page_history_index


class BuildIndex(Command):
    '(re)builds GitPages indexes'

    def handle(self, app, *args, **kwargs):

        with app.test_request_context():
            try:
                ui.setup_gitpages_application()
                ui.setup_gitpages()
                return self.run(*args, **kwargs)
            finally:
                ui.teardown_gitpages()

    def run(self):

        build_page_history_index(
            index=current_app.history_index,
            repo=current_app.repo,
            ref=current_app.default_ref,
        )

        build_date_index(
            index=current_app.date_index,
            repo=current_app.repo,
            ref=current_app.default_ref,
        )
