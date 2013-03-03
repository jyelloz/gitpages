from .storage.git import find_pages, get_pages_tree


def build_date_index(index, repo, ref='HEAD'):

    from .util import slugify
    from dateutil.parser import parse as parse_date

    pages_tree = get_pages_tree(repo, ref)

    pages = find_pages(repo, pages_tree)

    w = index.writer()

    for page, attachments in pages:

        doctree = read_page_rst(page)
        title = get_title(doctree)
        docinfo = get_docinfo_as_dict(doctree)

        slug = slugify(title)

        print 'title is %r, slug is %r' % (title, slug)

        w.add_document(
            date=parse_date(docinfo['date']),
            slug=slugify(title),
            title=unicode(title),
            ref_id=unicode(ref),
            # TODO: add support for these
            blob_id=None,
            blob_id__ref_id=None,
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
