# -*- coding: utf-8 -*-

from flask import Flask
from flask_failsafe import failsafe
from jinja2 import ChoiceLoader, FileSystemLoader

from typogrify.templatetags.jinja_filters import register as register_typogrify

from .converters import GitRefConverter, UuidConverter


@failsafe
def create(*args, **kwargs):

    from . import ui

    application = Flask(__name__, *args, **kwargs)
    application.url_map.converters['git_ref'] = GitRefConverter
    application.url_map.converters['uuid'] = UuidConverter

    register_typogrify(application.jinja_env)

    gitpages_web_ui = ui.create_blueprint()
    application.register_blueprint(gitpages_web_ui)

    return application
