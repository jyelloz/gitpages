# -*- coding: utf-8 -*-

from typing import Optional
from collections.abc import Callable

from flask import Flask, Blueprint
from flask_failsafe import failsafe

from typogrify.templatetags.jinja_filters import register as register_typogrify

from .converters import GitRefConverter, UuidConverter


@failsafe
def create(*args, **kwargs) -> Flask:

    application = Flask(__name__, *args, **kwargs)

    register_gitpages_blueprint(application)

    return application


def register_gitpages_blueprint(
    application: Flask,
    extra_config: Optional[Callable[[Blueprint], Blueprint]]=None,
) -> Flask:

    from . import ui

    application.url_map.converters['git_ref'] = GitRefConverter
    application.url_map.converters['uuid'] = UuidConverter

    register_typogrify(application.jinja_env)

    gitpages_web_ui = ui.create_blueprint()
    if extra_config:
        gitpages_web_ui = extra_config(gitpages_web_ui)

    application.register_blueprint(gitpages_web_ui)

    return application
