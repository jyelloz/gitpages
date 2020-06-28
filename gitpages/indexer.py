# -*- coding: utf-8 -*-

from datetime import datetime
from posixpath import dirname
from os import makedirs, error as OSError
from os.path import isdir

from typing import Iterable

from dateutil.parser import parse as parse_date
from dateutil.tz import tzoffset
from dulwich.walk import Walker
from dulwich.repo import BaseRepo
from dulwich.objects import Blob, Commit

from whoosh import index
from whoosh.fields import Schema
from whoosh.index import Index
from whoosh.writing import IndexWriter


from .storage import git as git_storage
from .storage.git import PageAttachment
from .util import slugify
from .util.compat import (
    _bytes_to_text as bytes_to_text,
    _text_to_bytes as text_to_bytes,
)
from .web import api


def makedirs_quiet(path):

    try:
        makedirs(path)
    except OSError:
        if not isdir(path):
            raise


def get_index(index_path: str, index_name: str, schema: Schema) -> Index:

    makedirs_quiet(index_path)

    if index.exists_in(index_path, index_name):
        return index.open_dir(
            index_path,
            indexname=index_name,
        )

    return index.create_in(
        index_path,
        schema=schema,
        indexname=index_name,
    )


def write_page(
        writer: IndexWriter,
        path: str,
        page: Blob,
        attachments: Iterable,
):

    doctree = read_page_rst(page.data)
    title = get_title(doctree)
    docinfo = get_docinfo_as_dict(doctree)

    slug = slugify(title)
    date = parse_date(docinfo['date'])
    status = docinfo['status']
    blob_id = bytes_to_text(page.id)

    rendered = render_page(page)

    writer.add_document(
        kind='page',
        page_date=date,
        page_slug=slug,
        page_title=title,
        page_status=status,
        page_path=path,
        page_blob_id=blob_id,
        page_rendered=rendered,
    )

    writer.add_document(kind='page-dummy-child')

    for attachment in attachments:
        write_page_attachment(writer, attachment)


def write_revision(
        repo: BaseRepo,
        writer: IndexWriter,
        commit: Commit,
        path: str,
):

    path_bytes = text_to_bytes(path)

    tree_id = commit.tree
    tree = repo[tree_id]
    _mode, blob_id = tree.lookup_path(
        repo.get_object,
        path_bytes,
    )

    commit_time = datetime.fromtimestamp(
        commit.commit_time,
        tzoffset(None, commit.commit_timezone),
    )

    author_time = datetime.fromtimestamp(
        commit.author_time,
        tzoffset(None, commit.author_timezone),
    )

    page_blob = repo[blob_id]

    doctree = read_page_rst(page_blob.data)
    title = get_title(doctree)
    slug = slugify(title)
    docinfo = get_docinfo_as_dict(doctree)
    date = parse_date(docinfo['date'])
    status = docinfo['status']

    page_tree_path = dirname(path)
    page_tree_path_bytes = text_to_bytes(page_tree_path)

    _page_tree_mode, page_tree_id = tree.lookup_path(
        repo.get_object,
        page_tree_path_bytes,
    )

    page_tree = repo[page_tree_id]
    attachments = git_storage.load_page_attachments(repo, page_tree)

    rendered = render_page(page_blob)

    with writer.group():

        writer.add_document(
            kind='revision',
            revision_date=date,
            revision_slug=slug,
            revision_title=title,
            revision_status=status,
            revision_path=path,
            revision_blob_id=bytes_to_text(blob_id),
            revision_commit_id=bytes_to_text(commit.id),
            revision_tree_id=bytes_to_text(tree_id),
            revision_author=bytes_to_text(commit.author),
            revision_committer=bytes_to_text(commit.committer),
            revision_author_time=author_time,
            revision_commit_time=commit_time,
            revision_message=bytes_to_text(commit.message),
            revision_rendered=rendered,
        )

        writer.add_document(kind='revision-dummy-child')

        for attachment in attachments:
            write_revision_attachment(writer, attachment)


def write_page_attachment(writer, attachment):
    _write_attachment(writer, attachment, kind='page-attachment')


def write_revision_attachment(writer, attachment):
    _write_attachment(writer, attachment, kind='revision-attachment')


def _write_attachment(
        writer: IndexWriter,
        attachment: PageAttachment,
        kind: str,
):

    attachment_tree_id = attachment.tree_id_text
    metadata_blob_id = attachment.metadata_blob_id_text
    data_blob_id = attachment.blob_id_text
    doctree = read_page_rst(attachment.metadata.data)
    docinfo = get_docinfo_as_dict(doctree)

    content_disposition = docinfo.get(
        'content-disposition',
        'inline',
    )
    content_length = attachment.data.raw_length()
    content_type = docinfo.get(
        'content-type',
        'application/octet-stream',
    )

    writer.add_document(
        kind=kind,
        attachment_content_type=content_type,
        attachment_content_length=content_length,
        attachment_content_disposition=content_disposition,
        attachment_metadata_blob_id=metadata_blob_id,
        attachment_data_blob_id=data_blob_id,
        attachment_id=attachment_tree_id,
    )


def build_hybrid_index(index: Index, repo: BaseRepo, ref: bytes=b'HEAD'):

    head = repo.refs[ref]

    def get_revisions(path) -> Walker:

        from posixpath import dirname

        parent_path_bytes = text_to_bytes(dirname(path))

        return Walker(
            store=repo.object_store,
            include=[head],
            paths=[parent_path_bytes],
            follow=True,
        )

    head_pages_tree = git_storage.get_pages_tree(repo, ref)

    pages = git_storage.find_pages(repo, head_pages_tree)

    pages_data = git_storage.load_pages_with_attachments(repo, pages)

    with index.writer() as writer:

        for path, page, attachments in pages_data:

            revisions = get_revisions(path)

            with writer.group():

                write_page(writer, path, page, attachments)
                for revision in revisions:
                    write_revision(repo, writer, revision.commit, path)


def read_page_rst(page_rst):

    from docutils.core import publish_doctree

    return publish_doctree(page_rst)


def get_title(doctree) -> str:

    return next(
        (c for c in doctree.children
         if c.tagname == 'title')
    ).astext()


def get_docinfo_as_dict(doctree):

    def field_to_tuple(field):
        children = dict(
            (c.tagname, c)
            for c in field.children
        )

        return (
            children['field_name'].astext(),
            children['field_body'].astext(),
        )

    def docinfo_as_dict(docinfo):

        docinfo_dict = {}

        for child in docinfo.children:
            if child.tagname == 'field':
                name, value = field_to_tuple(child)
                docinfo_dict[name] = value
            else:
                docinfo_dict[child.tagname] = child.astext()

        return docinfo_dict

    docinfo = next(
        (c for c in doctree.children
         if c.tagname == 'docinfo')
    )

    return docinfo_as_dict(docinfo)

def render_page(blob: Blob):
    return api.render_page_content(bytes_to_text(blob.data))
