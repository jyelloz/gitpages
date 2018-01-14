# -*- coding: utf-8 -*-

import logging
from datetime import datetime

from dateutil.parser import parse as parse_date
from dateutil.tz import tzoffset
from dulwich.walk import Walker

from .storage import git as git_storage
from .util import slugify


_log = logging.getLogger(__name__)


def get_index(index_path, index_name, schema):

    from os import makedirs
    from os.path import isdir

    from whoosh import index

    try:
        makedirs(index_path)
    except:
        if not isdir(index_path):
            raise

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


def write_page(repo, writer, path, page, attachments):
    """
    :type repo: dulwich.repo.BaseRepo
    :type writer: whoosh.writing.IndexWriter
    :type path: six.text_type
    :type page: dulwich.objects.Blob
    """

    doctree = read_page_rst(page.data)
    title = get_title(doctree)
    docinfo = get_docinfo_as_dict(doctree)

    slug = slugify(title)
    date = parse_date(docinfo['date'])
    status = docinfo['status']
    blob_id = unicode(page.id)

    writer.add_document(
        kind=u'page',
        page_date=date,
        page_slug=slug,
        page_title=unicode(title),
        page_status=unicode(status),
        page_path=unicode(path),
        page_blob_id=blob_id,
    )

    for attachment in attachments:
        write_page_attachment(writer, attachment)


def write_revision(repo, writer, commit, path):

    from posixpath import dirname

    tree_id = commit.tree
    tree = repo[tree_id]
    mode, blob_id = tree.lookup_path(repo.get_object, path)

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

    page_tree_mode, page_tree_id = tree.lookup_path(
        repo.get_object,
        page_tree_path,
    )

    page_tree = repo[page_tree_id]
    attachments = git_storage.load_page_attachments(repo, page_tree)

    with writer.group():

        writer.add_document(
            kind=u'revision',
            revision_date=date,
            revision_slug=unicode(slug),
            revision_title=unicode(title),
            revision_status=unicode(status),
            revision_path=unicode(path),
            revision_blob_id=unicode(blob_id),
            revision_commit_id=unicode(commit.id),
            revision_tree_id=unicode(tree_id),
            revision_author=unicode(commit.author),
            revision_committer=unicode(commit.committer),
            revision_author_time=author_time,
            revision_commit_time=commit_time,
            revision_message=unicode(commit.message),
        )

        for attachment in attachments:
            write_revision_attachment(writer, attachment)


def write_page_attachment(writer, attachment):
    _write_attachment(writer, attachment, kind=u'page-attachment')


def write_revision_attachment(writer, attachment):
    _write_attachment(writer, attachment, kind=u'revision-attachment')


def _write_attachment(writer, attachment, kind):
    """
    :type writer: whoosh.writing.IndexWriter
    :type attachment: gitpages.storage.git.PageAttachment
    :type kind: six.text_type
    """

    (
        attachment_tree_id,
        data_blob_id, metadata_blob_id,
        data_callable, metadata_callable,
    ) = attachment

    doctree = read_page_rst(metadata_callable().data)
    docinfo = get_docinfo_as_dict(doctree)

    content_disposition = docinfo.get(
        'content-disposition',
        'inline',
    )
    content_length = data_callable().raw_length()
    content_type = docinfo.get(
        'content-type',
        'application/octet-stream',
    )

    writer.add_document(
        kind=kind,
        attachment_content_type=unicode(content_type),
        attachment_content_length=content_length,
        attachment_content_disposition=unicode(content_disposition),
        attachment_metadata_blob_id=unicode(metadata_blob_id),
        attachment_data_blob_id=unicode(data_blob_id),
        attachment_id=unicode(attachment_tree_id),
    )


def build_hybrid_index(index, repo, ref='HEAD'):
    """
    :type index: whoosh.index.Index
    :type repo: dulwich.repo.BaseRepo
    :type ref: six.text_type
    """

    head = repo.refs[ref]

    def get_revisions(path):

        from posixpath import dirname

        return Walker(
            store=repo.object_store,
            include=[head],
            paths=[dirname(path)],
            follow=True,
        )

    head_pages_tree = git_storage.get_pages_tree(repo, ref)

    pages = git_storage.find_pages(repo, head_pages_tree)

    pages_data = git_storage.load_pages_with_attachments(repo, pages)

    w = index.writer()

    try:

        for path, page, attachments in pages_data:

            with w.group():

                write_page(repo, w, path, page, attachments)
                revisions = get_revisions(path)
                for revision in revisions:
                    write_revision(repo, w, revision.commit, path)

        w.commit(optimize=True)

    except:

        w.cancel()
        raise


def read_page_rst(page_rst):

    from docutils.core import publish_doctree

    return publish_doctree(page_rst)


def get_title(doctree):

    return next(
        (c for c in doctree.children
         if c.tagname is 'title')
    ).astext()


def get_docinfo_as_dict(doctree):

    def field_to_tuple(field):
        children = dict(
            (c.tagname, c)
            for c in field.children
        )

        return (
            str(children['field_name'].astext()),
            children['field_body'].astext(),
        )

    def docinfo_as_dict(docinfo):

        docinfo_dict = {}

        for c in docinfo.children:
            if c.tagname is 'field':
                name, value = field_to_tuple(c)
                docinfo_dict[name] = value
            else:
                docinfo_dict[c.tagname] = c.astext()

        return docinfo_dict

    docinfo = next(
        (c for c in doctree.children
         if c.tagname is 'docinfo')
    )

    return docinfo_as_dict(docinfo)
