# -*- coding: utf-8 -*-

from docutils.writers.html4css1 import HTMLTranslator, Writer
from docutils.nodes import Inline, TextElement
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

    def starttag(self, node, tagname, *args, **kwargs):
        return HTMLTranslator.starttag(
            self,
            node,
            'code' if tagname.lower() == 'tt' else tagname,
            *args,
            **kwargs
        )

    def visit_strikethrough(self, node):
        self.body.append(self.starttag(node, 'del', ''))

    def depart_strikethrough(self, node):
        self.body.append('</del>')
