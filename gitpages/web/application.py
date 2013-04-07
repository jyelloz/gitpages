# -*- coding: utf-8 -*-

from flask import Flask
from flask_failsafe import failsafe

from typogrify.templatetags.jinja_filters import register as register_typogrify

from .converters import GitRefConverter, UuidConverter


@failsafe
def create(*args, **kwargs):

    application = Flask(__name__, *args, **kwargs)

    register_gitpages_blueprint(application)

    return application


def register_gitpages_blueprint(application):

    from . import ui

    application.url_map.converters['git_ref'] = GitRefConverter
    application.url_map.converters['uuid'] = UuidConverter

    register_typogrify(application.jinja_env)

    gitpages_web_ui = ui.create_blueprint()
    application.register_blueprint(gitpages_web_ui)

    return application
