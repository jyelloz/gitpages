from whoosh.fields import Schema, ID, DATETIME, TEXT


class ByDate(Schema):

    date = DATETIME(stored=True, sortable=True)
    blob_id = ID(stored=True)
    slug = TEXT(stored=True)
    title = TEXT(stored=True)
    ref = ID(stored=True)


class PageHistory(Schema):

    blob_id = ID(stored=True)
    parent_id = ID(stored=True)
    date = DATETIME(stored=True, sortable=True)
    ref = ID(stored=True)
