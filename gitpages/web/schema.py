# -*- coding: utf-8 -*-

from whoosh.fields import SchemaClass, ID, DATETIME, TEXT, NUMERIC


class DateRevisionHybrid(SchemaClass):

    kind = ID(stored=True)
    date = DATETIME(stored=True)
    slug = ID(stored=True)
    title = TEXT(stored=True)
    status = ID(stored=True)
    path = ID(stored=True)

    author = ID(stored=True)
    committer = ID(stored=True)

    author_time = DATETIME(stored=True)
    commit_time = DATETIME(stored=True)

    message = TEXT(stored=True)

    blob_id = ID(stored=True)
    commit_id = ID(stored=True)
    tree_id = ID(stored=True)

    attachment_id = ID(stored=True)
    attachment_data_blob_id = ID(stored=True)
    attachment_metadata_blob_id = ID(stored=True)
    attachment_content_type = ID(stored=True)
    attachment_content_disposition = ID(stored=True)
    attachment_content_length = NUMERIC(stored=True)
