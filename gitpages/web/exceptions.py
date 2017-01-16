# -*- coding: utf-8 -*-

import six


class PageNotFound(Exception):

    def __init__(self, *args):

        super(PageNotFound, self).__init__()

        self.args = args

    def __unicode__(self):

        return u', '.join(repr(arg) for arg in self.args)

    def __repr__(self):

        return '<%s %s>' % (self.__class__.__name__, self)

    __str__ = __unicode__


class AttachmentNotFound(Exception):

    def __init__(self, tree_id):

        super(AttachmentNotFound, self).__init__()

        self.tree_id = tree_id

    def __unicode__(self):

        return six.text_type(repr(self.tree_id))

    def __repr__(self):

        return '<%s %s>' % (self.__class__.__name__, self)

    __str__ = __unicode__
