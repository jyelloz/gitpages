# -*- coding: utf-8 -*-

'''
This is all code that I did not write.
'''

import re

from unidecode import unidecode
from functools import wraps

from docutils.nodes import SkipNode

from flask import current_app


_stripped_re = re.compile(r'[()]+')
_punct_re = re.compile(r'[\t !"#$%&\'()*\-/<=>?@\[\\\]^_`{|},.;]+')

"""
taken from
http://flask.pocoo.org/snippets/5/
"""


def slugify(text, delim=u'-'):
    """Generates an ASCII-only slug."""

    result = []

    text_stripped = _stripped_re.sub('', text.lower())

    for word in _punct_re.split(text_stripped):
        result.extend(unidecode(word).split())

    return unicode(delim.join(result))


def cached(key, key_builder=None, timeout=5 * 60):

    def decorator(f):

        @wraps(f)
        def decorated_function(*args, **kwargs):

            cache = current_app.config['CACHE']

            if callable(key_builder):
                cache_key = key % key_builder(args[0])
            else:
                cache_key = key % args[0]

            cached_value = cache.get(cache_key)
            if cached_value is not None:
                return cached_value

            value = f(*args, **kwargs)
            cache.set(cache_key, value, timeout=timeout)
            return value

        return decorated_function

    return decorator


def html5_visit_literal(self, node):
    # special case: "code" role
    classes = node.get('classes', [])
    if 'code' in classes:
        # filter 'code' from class arguments
        node['classes'] = [cls for cls in classes if cls != 'code']
        self.body.append(self.starttag(node, 'code', ''))
        return
    self.body.append(
        self.starttag(node, 'span', '', CLASS='docutils literal'))
    text = node.astext()
    for token in self.words_and_spaces.findall(text):
        if token.strip():
            # Protect text like "--an-option" and the regular expression
            # ``[+]?(\d+(\.\d*)?|\.\d+)`` from bad line wrapping
            if self.sollbruchstelle.search(token):
                self.body.append(
                    '<span class="pre">%s</span>' % self.encode(token)
                )
            else:
                self.body.append(self.encode(token))
        elif token in ('\n', ' '):
            # Allow breaks at whitespace:
            self.body.append(token)
        else:
            # Protect runs of multiple spaces; the last space can wrap:
            self.body.append('&nbsp;' * (len(token) - 1) + ' ')
    self.body.append('</span>')
    # Content already processed:
    raise SkipNode


def html5_visit_system_message(self, node):
    self.body.append(self.starttag(node, 'div', CLASS='system-message'))
    self.body.append('<p class="system-message-title">')
    backref_text = ''
    if len(node['backrefs']):
        backrefs = node['backrefs']
        if len(backrefs) == 1:
            backref_text = ('; <em><a href="#%s">backlink</a></em>'
                            % backrefs[0])
        else:
            i = 1
            backlinks = []
            for backref in backrefs:
                backlinks.append('<a href="#%s">%s</a>' % (backref, i))
                i += 1
            backref_text = ('; <em>backlinks: %s</em>'
                            % ', '.join(backlinks))
    if node.hasattr('line'):
        line = ', line %s' % node['line']
    else:
        line = ''
    self.body.append(
        'System Message: %s/%s (<span class="docutils tt">%s</span>%s)%s</p>\n'
        % (
            node['type'],
            node['level'],
            self.encode(node['source']),
            line,
            backref_text
        )
    )
