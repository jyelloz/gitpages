from flask import Flask
from flask_failsafe import failsafe

from .converters import GitRefConverter, UuidConverter


@failsafe
def create():

    from . import ui

    application = Flask(__name__)
    application.url_map.converters['git_ref'] = GitRefConverter
    application.url_map.converters['uuid'] = UuidConverter

    gitpages_web_ui = ui.create_blueprint()
    application.register_blueprint(gitpages_web_ui)

    return application
