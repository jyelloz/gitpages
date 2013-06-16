# -*- coding: utf-8 -*-

from docutils.writers.html4css1 import HTMLTranslator, Writer
from docutils.nodes import Inline, TextElement, SkipNode
from docutils.parsers.rst.roles import register_local_role


class strikethrough(Inline, TextElement):
    pass


def strike(name, rawtext, text, lineno, inliner, options={}, content={}):
    return [strikethrough(rawsource=rawtext, text=text)], []


def register_roles():
    register_local_role('strikethrough', strike)


class GitPagesWriter(Writer):

    def __init__(self):
        Writer.__init__(self)
        self.translator_class = GitPagesHTMLTranslator


class GitPagesHTMLTranslator(HTMLTranslator):

    def __init__(self, document):
        HTMLTranslator.__init__(self, document)

    def visit_strikethrough(self, node):
        self.body.append(self.starttag(node, 'del', ''))

    def depart_strikethrough(self, node):
        self.body.append('</del>')

    def visit_literal(self, node):
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
                    self.body.append('<span class="pre">%s</span>'
                                     % self.encode(token))
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

    def visit_system_message(self, node):
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
        self.body.append('System Message: %s/%s '
                         '(<span class="docutils tt">%s</span>%s)%s</p>\n'
                         % (node['type'], node['level'],
                            self.encode(node['source']), line, backref_text))
