# -*- coding: utf-8 -*-


class PageNotFound(Exception):

    def __init__(self, *args):

        super(PageNotFound, self).__init__()

        self.args = args

    def __unicode__(self):

        return u', '.join(repr(arg) for arg in self.args)

    def __str__(self):

        return unicode(self).encode('utf-8')

    def __repr__(self):

        return '<%s \'%s\'>' % (self.__class__.__name__, self)


class AttachmentNotFound(Exception):

    def __init__(self, tree_id):

        super(AttachmentNotFound, self).__init__()

        self.tree_id = tree_id

    def __unicode__(self):

        return unicode(repr(self.tree_id))

    def __str__(self):

        return unicode(self).encode('utf-8')

    def __repr__(self):

        return '<%s \'%s\'>' % (self.__class__.__name__, self)
