# -*- coding: utf-8 -*-

from whoosh.fields import SchemaClass, ID, DATETIME, TEXT, NUMERIC


class DateRevisionHybrid(SchemaClass):

    kind = ID(stored=True)

    page_date = DATETIME(stored=True)
    page_slug = ID(stored=True)
    page_title = TEXT(stored=True)
    page_status = ID(stored=True)
    page_path = ID(stored=True)
    page_blob_id = ID(stored=True)

    revision_date = DATETIME(stored=True)
    revision_slug = ID(stored=True)
    revision_title = TEXT(stored=True)
    revision_status = ID(stored=True)
    revision_path = ID(stored=True)
    revision_blob_id = ID(stored=True)
    revision_commit_id = ID(stored=True)
    revision_tree_id = ID(stored=True)
    revision_author = ID(stored=True)
    revision_committer = ID(stored=True)
    revision_author_time = DATETIME(stored=True)
    revision_commit_time = DATETIME(stored=True)
    revision_message = TEXT(stored=True)

    attachment_id = ID(stored=True)
    attachment_data_blob_id = ID(stored=True)
    attachment_metadata_blob_id = ID(stored=True)
    attachment_content_type = ID(stored=True)
    attachment_content_disposition = ID(stored=True)
    attachment_content_length = NUMERIC(stored=True)
