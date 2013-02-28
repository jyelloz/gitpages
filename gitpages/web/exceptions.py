# -*- coding: utf-8 -*-


class PageNotFound(Exception):

    def __init__(self, date, slug, ref):

        super(PageNotFound, self).__init__()

        self.date = date
        self.slug = slug
        self.ref = ref

    def __unicode__(self):

        return u'%r, %r, %r' % (self.date, self.slug, self.ref)

    def __str__(self):

        return unicode(self).encode('utf-8')

    def __repr__(self):

        return '<%s \'%s\'>' % (self.__class__.__name__, self)
