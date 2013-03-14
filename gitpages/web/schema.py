# -*- coding: utf-8 -*-

from whoosh.fields import SchemaClass, ID, DATETIME, TEXT


class ByDate(SchemaClass):

    date = DATETIME(stored=True)
    blob_id = ID(stored=True)
    slug = ID(stored=True)
    title = TEXT(stored=True)
    status = ID(stored=True)
    ref_id = ID(stored=True)
    blob_id__ref_id = ID(stored=False, unique=True)
    path = ID(stored=True)


class PageHistory(SchemaClass):

    blob_id = ID(stored=True)
    parent_id = ID(stored=True)
    date = DATETIME(stored=True)
    ref = ID(stored=True)
    path = ID(stored=True)


class RevisionHistory(SchemaClass):

    ref = ID(stored=True)
    commit_id = ID(stored=True)
    tree_id = ID(stored=True)

    author = ID(stored=True)
    committer = ID(stored=True)

    author_time = DATETIME(stored=True)
    commit_time = DATETIME(stored=True)

    message = TEXT(stored=True)
    path = ID(stored=True)
