# -*- coding: utf-8 -*-

from datetime import datetime, timedelta

from whoosh.query import Term, DateRange

from .exceptions import PageNotFound


class Page(object):

    def __init__(self, slug, ref, text, history):
        self.slug = slug
        self.ref = ref
        self.text = text
        self.history = history


class GitPages(object):

    _max_timedelta = timedelta(days=1)

    def __init__(self, repo, date_index, history_index):
        self._repo = repo
        self._date_index = date_index
        self._history_index = history_index

    def page(self, date, slug, ref):

        earliest = datetime(date.year, date.month, date.day)
        latest = earliest + GitPages._max_timedelta

        query = (
            Term('slug', unicode(slug)) &
            DateRange(
                'date',
                start=earliest,
                end=latest,
                startexcl=False,
                endexcl=True,
            )
        )

        with self._date_index.searcher() as s:

            results = s.search(query, limit=1)

            if results.is_empty():
                raise PageNotFound(date, slug, ref)

            page_result = results[0]
            blob = self._repo.get_blob(page_result.blob_id)

            return Page(slug, ref, blob, [])

    def history(self, page):
        return page_history(page.slug)

    def older_pages(self, page):
        pass

    def newer_pages(self, page):
        pass

    def teardown(self):

        try:
            self._date_index.close()
        except:
            pass

        try:
            self._history_index.close()
        except:
            pass


def page(page_pk, ref='HEAD'):
    return Page(
        page_pk,
        ref,
        list(page_history(page_pk))
    )


def page_history(page_pk):
    import random

    length = random.randint(1, 20)

    return (
        'revision %d of page#%s' % (i, page_pk)
        for i in xrange(1, length + 1)
    )
