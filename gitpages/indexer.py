# -*- coding: utf-8 -*-

from logging import getLogger as get_logger

from .storage.git import find_pages, get_pages_tree


_log = get_logger(__name__)


def build_date_index(index, repo, ref='HEAD'):

    from .util import slugify
    from dateutil.parser import parse as parse_date

    pages_tree = get_pages_tree(repo, ref)

    pages = find_pages(repo, pages_tree)

    w = index.writer()

    for page, attachments in pages:

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
        )

    w.commit()


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
