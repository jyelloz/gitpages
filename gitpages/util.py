# -*- coding: utf-8 -*-

"""
taken from
http://flask.pocoo.org/snippets/5/
"""

import re
from unidecode import unidecode
from functools import wraps
from werkzeug.contrib.cache import SimpleCache

_punct_re = re.compile(r'[\t !"#$%&\'()*\-/<=>?@\[\\\]^_`{|},.;]+')


def slugify(text, delim=u'-'):
    """Generates an ASCII-only slug."""

    result = []

    for word in _punct_re.split(text.lower()):
        result.extend(unidecode(word).split())

    return unicode(delim.join(result))


_cache = SimpleCache()


def cached(key, key_builder=None, timeout=5 * 60):

    def decorator(f):

        @wraps(f)
        def decorated_function(*args, **kwargs):

            if key_builder:
                cache_key = key % key_builder(args[0])
            else:
                cache_key = key % args[0]

            cached_value = _cache.get(cache_key)
            if cached_value is not None:
                return cached_value

            value = f(*args, **kwargs)
            _cache.set(cache_key, value, timeout=timeout)
            return value

        return decorated_function

    return decorator
