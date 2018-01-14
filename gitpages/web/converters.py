# -*- coding: utf-8 -*-

from six.moves.urllib.parse import quote_plus, unquote_plus
import six
from uuid import UUID

from werkzeug.routing import BaseConverter


class GitRefConverter(BaseConverter):

    def __init__(self, url_map, *args):
        super(GitRefConverter, self).__init__(url_map)

    def to_python(self, value):
        return unquote_plus(unquote_plus(value))

    def to_url(self, value):
        return quote_plus(quote_plus(value))


class UuidConverter(BaseConverter):

    def __init__(self, url_map, *args):
        super(UuidConverter, self).__init__(url_map)

    def to_python(self, value):
        return UUID(value)

    def to_url(self, value):
        return six.text_type(value)
