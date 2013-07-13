# -*- coding: utf-8 -*-

from docutils.writers.html4css1 import HTMLTranslator, Writer
from docutils.nodes import Inline, TextElement
from docutils.parsers.rst.roles import register_local_role

from ..stolen import html5_visit_literal, html5_visit_system_message


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

GitPagesHTMLTranslator.visit_literal = html5_visit_literal
GitPagesHTMLTranslator.visit_system_message = html5_visit_system_message
