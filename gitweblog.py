#!/usr/bin/env python

from os import makedirs as os_makedirs
from os.path import basename, dirname, join, isdir
from urllib import quote_plus, unquote_plus
import re
import functools


from flask import Flask, make_response, url_for
from werkzeug.routing import BaseConverter

from whoosh.fields import SchemaClass, TEXT, NUMERIC, DATETIME, ID
from whoosh.query import Term

import yaml
import pytz


MODULE_NAME = basename(__file__)[:-len('.py')]


def makedirs(path, mode=0755):
    try:
        os_makedirs(path, mode)
    except Exception, e:
        if not isdir(path):
            raise e


class GitRefConverter(BaseConverter):
    def __init__(self, url_map, *args):
        super(GitRefConverter, self).__init__(url_map)

    def to_python(self, value):
        return unquote_plus(unquote_plus(value))

    def to_url(self, value):
        return quote_plus(quote_plus(value))


class UuidConverter(BaseConverter):
    def __init__(self, url_map, *args):
        super(UuidConverter, self).__init__(url_map)

    def to_python(self, value):
        from uuid import UUID
        return UUID(value)

    def to_url(self, value):
        return unicode(value)


def find_published_pages(searcher):

    query = Term('status', u'published')

    return searcher.search(
        query,
        sortedby='published_at'
    )


gitweblog = Flask(MODULE_NAME)
gitweblog.url_map.converters['git_ref'] = GitRefConverter
gitweblog.url_map.converters['uuid'] = UuidConverter


@gitweblog.route('/')
def home():
    return make_response(
        '%s: Home\n' % MODULE_NAME,
        200,
        {
            'Content-Type': 'text/plain; charset=utf-8',
        }
    )


@gitweblog.route('/page/<path:path>', defaults={'ref': u'master'})
@gitweblog.route('/page/<path:path>!<git_ref:ref>')
def page(path, ref):

    url = url_for('page', path=path, ref=ref)

    data_yaml = yaml.dump(
        {
            'path': repr(path),
            'ref': repr(ref),
            'url': repr(unicode(url)),
        },
        default_flow_style=False
    )

    return make_response(
        data_yaml,
        200,
        {
            'Content-Type': 'text/x-yaml; charset=utf-8',
        }
    )


class PageSchema(SchemaClass):
    pk = NUMERIC(stored=True)
    title = TEXT(stored=True)
    sort_title = ID
    status = ID(stored=True)
    tree = NUMERIC(stored=True)
    created_at = DATETIME(stored=True)
    modified_at = DATETIME(stored=True)
    published_at = DATETIME(stored=True)


class PageAttachmentSchema(SchemaClass):
    pk = NUMERIC(stored=True)
    document_pk = NUMERIC(stored=True)
    filename = TEXT(stored=True)
    content_type = TEXT(stored=True)
    content_length = NUMERIC(stored=True)


class GitTreeSchema(SchemaClass):
    pass


tw_pattern = re.compile(
    r'^(.*?)(?:\s*?)$',
    flags=re.UNICODE | re.MULTILINE
)
tn_pattern = re.compile(
    r'[\r\n]+\Z',
    flags=re.UNICODE | re.MULTILINE
)


def strip_trailing_whitespace(s):
    return tw_pattern.sub(
        r'\1',
        tn_pattern.sub(
            '',
            s
        )
    )


def convert_django_page(page):

    los_angeles_tz = pytz.timezone('America/Los_Angeles')

    def localize(dt):
        if dt.tzinfo is not None:
            return los_angeles_tz.normalize(dt.astimezone(los_angeles_tz))
        return los_angeles_tz.localize(dt)

    def localize_better(dt):
        return dt.astimezone(los_angeles_tz)

    pages_directory = join(dirname(__file__), 'database', 'page')

    title = page.title
    title_under = u'=' * len(title)
    # absolute_url = page.get_absolute_url()
    body_text = strip_trailing_whitespace(
        convert_django_pagepart(
            page.pagepart_set.filter(name='body').get()
        )
    )
    page_id = page.id

    page_directory = join(pages_directory, page_id)
    print 'making directory %s' % page_directory
    makedirs(page_directory)

    published_at = localize(page.published_at)
    created_at = localize(page.created_at)
    modified_at = localize(page.modified_at)

    rst_text = u'''\
%s
%s

:Author: Jordan Yelloz
:date: %s
:status: %s

:date created: %s
:date modified: %s

%s\
''' % (
        title,
        title_under,
        published_at,
        page.status,
        created_at,
        modified_at,
        body_text,
    )

    page_rst = join(page_directory, 'page.rst')
    with open(page_rst, 'wb') as f:
        print >> f, rst_text

    attachments = page.pageattachment_set.all()
    for a in attachments:
        convert_django_pageattachment(a, page_directory)


def convert_django_pagepart(part):
    return part.text.replace('\r\n', '\n')


def convert_django_pageattachment(attachment, page_directory):

    if attachment.content_transfer_encoding == u'base64':
        from base64 import b64decode
        content = b64decode(attachment.data)
    else:
        content = attachment.data.replace('\r\n', '\n')
        content = strip_trailing_whitespace(
            content
        ) + '\n'

    attachment_id = attachment.id

    attachment_directory = join(page_directory, 'attachment', attachment_id)
    metadata_file = join(attachment_directory, 'metadata.rst')
    data_file = join(attachment_directory, 'data')

    metadata_rst = u'''\
:filename: %s
:content-type: %s
:content-length: %d\
''' % (
        attachment.filename,
        attachment.content_type,
        len(content),
    )

    print 'creating attachment directory %s' % attachment_directory
    makedirs(attachment_directory)

    with open(metadata_file, 'wb') as f:
        print >> f, metadata_rst

    with open(data_file, 'wb') as f:
        f.write(content)


def find_pages(repository, pages_tree):

    page_items = pages_tree.iteritems()

    page_tree_shas = (entry.sha for entry in page_items)
    page_trees = (repository.tree(sha) for sha in page_tree_shas)

    return (load_page_data(repository, page_tree) for page_tree in page_trees)


def load_page_data(repository, page_tree):

    page_rst = [i for i in page_tree.iteritems() if i.path == 'page.rst'].pop()

    page_rst_blob = repository.get_blob(page_rst.sha)

    return page_rst_blob.data, load_page_attachments(repository, page_tree)


def load_page_attachments(repository, page_tree):

    def load_page_attachment(attachment_tree):

        metadata_rst = [
            i for i in attachment_tree.iteritems() if i.path == 'metadata.rst'
        ].pop()
        data = [
            i for i in attachment_tree.iteritems() if i.path == 'data'
        ].pop()

        metadata = repository.get_blob(metadata_rst.sha).data
        data_callable = functools.partial(repository.get_blob, data.sha)

        return metadata, data_callable

    attachments_items = [
        i for i in page_tree.iteritems() if i.path == 'attachment'
    ]

    if len(attachments_items) < 1:
        return []

    attachments = attachments_items.pop()

    page_attachments_tree = repository.tree(attachments.sha)

    page_attachment_trees = (
        repository.tree(t.sha) for t in page_attachments_tree.iteritems()
    )

    return (load_page_attachment(t) for t in page_attachment_trees)


if __name__ == '__main__':
    gitweblog.run(
        debug=True,
        host='0.0.0.0',
    )
