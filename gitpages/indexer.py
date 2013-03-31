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


def build_hybrid_index(index, repo, ref='HEAD'):

    head = repo.refs[ref]

    def get_revisions(path):
        return Walker(
            store=repo.object_store, include=[head], paths=[path], follow=True
        )

    def write_page(writer, path, page, attachments):

        doctree = read_page_rst(page.data)
        title = get_title(doctree)
        docinfo = get_docinfo_as_dict(doctree)

        slug = slugify(title)
        date = parse_date(docinfo['date'])
        status = docinfo['status']
        blob_id = unicode(page.id)

        writer.add_document(
            kind=u'page',
            date=date,
            slug=slug,
            title=unicode(title),
            status=unicode(status),
            blob_id=blob_id,
            path=unicode(path),
        )

    def write_revision(writer, commit, path):

        tree_id = commit.tree
        tree = repo.tree(tree_id)
        mode, blob_id = tree.lookup_path(repo.get_object, path)

        commit_time = datetime.fromtimestamp(
            commit.commit_time,
            tzoffset(None, commit.commit_timezone),
        )

        author_time = datetime.fromtimestamp(
            commit.author_time,
            tzoffset(None, commit.author_timezone),
        )

        page_blob = repo.get_blob(blob_id)

        doctree = read_page_rst(page_blob.data)
        title = get_title(doctree)
        docinfo = get_docinfo_as_dict(doctree)
        date = parse_date(docinfo['date'])
        status = docinfo['status']

        writer.add_document(
            kind=u'revision',
            commit_id=unicode(commit.id),
            tree_id=unicode(tree_id),
            blob_id=unicode(blob_id),
            author=unicode(commit.author),
            committer=unicode(commit.committer),
            commit_time=commit_time,
            author_time=author_time,
            message=unicode(commit.message),
            status=unicode(status),
            title=unicode(title),
            date=date,
        )

    head_pages_tree = git_storage.get_pages_tree(repo, ref)

    pages = git_storage.find_pages(repo, head_pages_tree)

    pages_data = git_storage.load_pages_with_attachments(repo, pages)

    w = index.writer()

    try:

        for path, page, attachments in pages_data:

            with w.group():

                write_page(w, path, page, attachments)
                revisions = get_revisions(path)
                for revision in revisions:
                    write_revision(w, revision.commit, path)

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
        children = {
            c.tagname: c
            for c in field.children
        }

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
