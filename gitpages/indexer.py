# -*- coding: utf-8 -*-

import logging

from .storage import git as git_storage


_log = logging.getLogger(__name__)


def build_date_index(index, repo, ref='HEAD'):

    from .util import slugify
    from dateutil.parser import parse as parse_date

    def visitor(pages):

        for path, page, page_rst_entry in pages:
            _log.debug('visiting blob %r @ %r', page_rst_entry.sha, path)
            yield path, page, page_rst_entry

    pages_tree = git_storage.get_pages_tree(repo, ref)

    pages = git_storage.find_pages(repo, pages_tree)
    pages_visited = visitor(pages)

    pages_data = git_storage.load_pages_with_attachments(repo, pages_visited)

    w = index.writer()

    try:

        for path, page, attachments in pages_data:

            doctree = read_page_rst(page.data)
            title = get_title(doctree)
            docinfo = get_docinfo_as_dict(doctree)

            slug = slugify(title)
            date = parse_date(docinfo['date'])
            status = docinfo['status']
            blob_id = unicode(page.id)

            w.add_document(
                date=date,
                slug=slug,
                title=unicode(title),
                ref_id=unicode(ref),
                status=unicode(status),
                blob_id=blob_id,
                blob_id__ref_id=(blob_id, ref),
                path=unicode(path),
            )

        w.commit(optimize=True)

    except:

        w.cancel()
        raise


def build_page_history_index(index, repo, ref='HEAD'):

    from datetime import datetime
    from dateutil.tz import tzoffset

    from dulwich.walk import Walker

    head = repo.ref(ref)

    walker = Walker(repo.object_store, [head])

    w = index.writer()

    try:

        for entry in walker:

            c = entry.commit

            commit_time = datetime.fromtimestamp(
                c.commit_time,
                tzoffset(None, c.commit_timezone),
            )

            author_time = datetime.fromtimestamp(
                c.author_time,
                tzoffset(None, c.author_timezone),
            )

            paths = (
                unicode(change.new.path)
                for change in entry.changes()
                if change.new.path is not None
            )

            for path in paths:
                w.add_document(
                    ref=unicode(ref),
                    commit_id=unicode(c.id),
                    tree_id=unicode(c.tree),
                    author=unicode(c.author),
                    committer=unicode(c.committer),
                    commit_time=commit_time,
                    author_time=author_time,
                    message=unicode(c.message),
                    path=path,
                )

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
