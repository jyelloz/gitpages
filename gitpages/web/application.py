from flask import Flask
from flask_failsafe import failsafe


@failsafe
def create():

    from . import ui

    gitpages_web_ui = ui.create_blueprint()

    application = Flask(ui.__name__)
    application.register_blueprint(gitpages_web_ui)

    return application
