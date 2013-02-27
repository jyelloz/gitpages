from flask import Flask
from flask_failsafe import failsafe


@failsafe
def create():

    from gitpages.web import ui

    gitpages_web_ui = ui.create_blueprint()

    application = Flask(ui.__name__)
    application.register_blueprint(gitpages_web_ui)

    return application

if __name__ == '__main__':
    create().run(debug=True, host='0.0.0.0')
