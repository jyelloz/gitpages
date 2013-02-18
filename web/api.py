class Page(object):

    def __init__(self, pk, history):
        self.pk = pk
        self.text = 'this is the text for page#%s' % pk
        self.history = history


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
