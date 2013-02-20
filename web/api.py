class Page(object):

    def __init__(self, pk, history):
        self.pk = pk
        self.text = 'this is the text for page#%s' % pk
        self.history = history


class GitPages(object):

    def __init__(self, repo, date_index, history_index):
        self._repo = repo
        self._date_index = date_index
        self._history_index = history_index

    def page(self, date, slug, ref):

        with self._date_index.searcher():
            pass

    def history(self, page):
        pass

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


def page(page_pk):
    return Page(
        page_pk,
        list(page_history(page_pk))
    )


def page_history(page_pk):
    import random

    length = random.randint(1, 20)

    return (
        'revision %d of page#%s' % (i, page_pk)
        for i in xrange(1, length + 1)
    )
