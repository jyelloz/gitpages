# -*- coding: utf-8 -*-

from flask import Flask
from flask_failsafe import failsafe
from jinja2 import ChoiceLoader, FileSystemLoader

from typogrify.templatetags.jinja_filters import register as register_typogrify

from .converters import GitRefConverter, UuidConverter


@failsafe
def create():

    from . import ui

    application = Flask(__name__)
    application.url_map.converters['git_ref'] = GitRefConverter
    application.url_map.converters['uuid'] = UuidConverter
    application.config.from_object('config')

    template_directories = application.config.get(
        'TEMPLATE_DIRECTORIES',
        None,
    )

    if template_directories:
        application.jinja_loader = ChoiceLoader([
            application.jinja_loader,
            FileSystemLoader(template_directories),
        ])

    register_typogrify(application.jinja_env)

    gitpages_web_ui = ui.create_blueprint()
    application.register_blueprint(gitpages_web_ui)

    return application
