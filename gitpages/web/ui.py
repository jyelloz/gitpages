# -*- coding: utf-8 -*-

import logging
from datetime import datetime
from six.moves.urllib.parse import urljoin

import pytz

from dateutil.relativedelta import relativedelta

from flask import (
    Blueprint, current_app, g, render_template, request, redirect, url_for
)
from werkzeug.exceptions import NotFound
from werkzeug.contrib.atom import AtomFeed

from .exceptions import PageNotFound, AttachmentNotFound
from .schema import DateRevisionHybrid
from .api import GitPages
from ..util import compat


_log = logging.getLogger(__name__)


def create_blueprint():

    gitpages_web_ui = Blueprint(
        'gitpages_web_ui',
        __name__,
        template_folder='templates',
    )

    gitpages_web_ui.add_url_rule(
        '/',
        'index_view',
        index_view_default_ref,
        defaults={
            'page_number': 1,
        },
    )

    gitpages_web_ui.add_url_rule(
        '/index/page/<int:page_number>/',
        'index_view',
        index_view_default_ref,
    )

    gitpages_web_ui.add_url_rule(
        '/feed/atom',
        'atom_feed',
        atom_feed,
    )
    gitpages_web_ui.add_url_rule(
        '/feed/rss',
        'rss_feed_redirect',
        rss_feed_redirect,
    )

    gitpages_web_ui.add_url_rule(
        '/' + '/'.join(
            [
                'archives',
                '<git_ref:tree_id>',
                '<int(fixed_digits=4):year>',
                '<int(fixed_digits=2):month>',
                '<int(fixed_digits=2):day>',
                '<slug>',
            ]
        ) + '/',
        'page_archive_view_ref',
        page_archive_view,
    )
    gitpages_web_ui.add_url_rule(
        '/' + '/'.join(
            [
                'archives',
                '<int(fixed_digits=4):year>',
                '<int(fixed_digits=2):month>',
                '<int(fixed_digits=2):day>',
                '<slug>',
            ]
        ) + '/',
        'page_archive_view',
        page_archive_view_default_ref,
    )

    gitpages_web_ui.add_url_rule(
        '/' + '/'.join(
            [
                'archives',
                '<int(fixed_digits=4):year>',
                '<int(fixed_digits=2):month>',
                '<int(fixed_digits=2):day>',
            ]
        ) + '/',
        'daily_archive',
        daily_archive_default,
        defaults={
            'page_number': 1,
        },
    )

    gitpages_web_ui.add_url_rule(
        '/' + '/'.join(
            [
                'archives',
                '<int(fixed_digits=4):year>',
                '<int(fixed_digits=2):month>',
            ]
        ) + '/',
        'monthly_archive',
        monthly_archive_default,
        defaults={
            'page_number': 1,
        },
    )

    gitpages_web_ui.add_url_rule(
        '/' + '/'.join(
            [
                'archives',
                '<int(fixed_digits=4):year>',
            ]
        ) + '/',
        'yearly_archive',
        yearly_archive_default,
        defaults={
            'page_number': 1,
        },
    )

    gitpages_web_ui.add_url_rule(
        '/' + '/'.join(
            [
                'attachment',
                '<git_ref:tree_id>',
            ]
        ),
        'attachment',
        attachment,
        defaults=dict(
            inline=False,
        ),
    )

    gitpages_web_ui.add_url_rule(
        '/' + '/'.join(
            [
                'attachment',
                '<git_ref:tree_id>',
                'inline',
            ]
        ),
        'inline_attachment',
        attachment,
        defaults=dict(
            inline=True,
        ),
    )

    gitpages_web_ui.before_app_first_request(setup_gitpages_application)
    gitpages_web_ui.before_request(setup_gitpages)
    gitpages_web_ui.teardown_request(teardown_gitpages)

    return gitpages_web_ui


def setup_gitpages_application():

    _log.debug('setting up blueprint')

    config = current_app.config

    repo = config['GITPAGES_REPOSITORY']
    ref = config['GITPAGES_DEFAULT_REF']

    index = config['GITPAGES_INDEX'](
        schema=DateRevisionHybrid()
    )

    current_app.repo = repo
    current_app.default_ref = compat._text_to_bytes(ref)
    current_app.allowed_statuses = config['GITPAGES_ALLOWED_STATUSES']
    current_app.timezone = config['TIMEZONE']
    current_app.index = index


def setup_gitpages():

    g.timezone = current_app.timezone
    g.utcnow = datetime.utcnow()
    g.searcher = current_app.index.searcher()
    g.gitpages = GitPages(
        current_app.repo,
        g.searcher,
    )
    g.allowed_statuses = current_app.allowed_statuses


def teardown_gitpages(exception=None):

    _log.debug('tearing down gitpages')

    gitpages = getattr(g, 'gitpages', None)
    searcher = getattr(g, 'searcher', None)

    if gitpages is not None:
        gitpages.teardown()

    if searcher is not None:
        searcher.close()


def index_view_default_ref(page_number):

    return index_view(page_number, current_app.default_ref)


def index_view(page_number, ref):

    results, results_page = g.gitpages.index(
        page_number, ref, statuses=g.allowed_statuses
    )

    return render_template(
        'index.html',
        index=results,
        results_page=results_page,
    )


def page_archive_view_default_ref(year, month, day, slug):

    return page_archive_view(year, month, day, slug, None)


def page_archive_view(year, month, day, slug, tree_id):

    try:

        date = g.timezone.localize(datetime(year, month, day))
        page = g.gitpages.page(date, slug, tree_id, g.allowed_statuses)

        attachments_date, attachments_slug, attachments_ref = (
            (date, slug, None) if tree_id is None
            else (page.info.revision_date, page.info.revision_slug, tree_id)
        )

        attachments = g.gitpages.attachments(
            attachments_date,
            attachments_slug,
            attachments_ref,
            g.allowed_statuses,
        )

        return page_view(page, attachments)

    except PageNotFound:
        raise NotFound()


def daily_archive_default(year, month, day, page_number):

    return daily_archive(
        year, month, day, current_app.default_ref, page_number
    )


def daily_archive(year, month, day, ref, page_number):

    earliest = g.timezone.localize(datetime(year, month, day))
    latest = earliest + relativedelta(days=1)

    return date_range_index(earliest, latest, ref, page_number)


def monthly_archive_default(year, month, page_number):

    return monthly_archive(year, month, current_app.default_ref, page_number)


def monthly_archive(year, month, ref, page_number):

    earliest = g.timezone.localize(datetime(year, month, 1))
    latest = earliest + relativedelta(months=1)

    return date_range_index(earliest, latest, ref, page_number)


def yearly_archive_default(year, page_number):

    return yearly_archive(year, current_app.default_ref, page_number)


def yearly_archive(year, ref, page_number):

    earliest = g.timezone.localize(datetime(year, 1, 1))
    latest = earliest + relativedelta(years=1)

    return date_range_index(earliest, latest, ref, page_number)


def date_range_index(earliest, latest, ref, page_number):

    results, results_page = g.gitpages.index(
        page_number,
        ref=ref,
        start_date=earliest,
        end_date=latest,
        start_date_excl=False,
        end_date_excl=True,
        statuses=g.allowed_statuses,
    )

    return render_template(
        'index.html',
        index=results,
        results_page=results_page,
    )


def attachment(tree_id, inline):

    from ..util import inlineify

    try:
        attachment = g.gitpages.attachment(tree_id)
        metadata = attachment.metadata

        content_disposition = (
            inlineify(metadata.content_disposition) if inline
            else metadata.content_disposition
        )

        return (
            attachment.data().data,
            200,
            {
                'Content-Type': metadata.content_type,
                'Content-Length': metadata.content_length,
                'Content-Disposition': content_disposition,
            },
        )

    except AttachmentNotFound:
        raise NotFound()


def atom_feed():

    config = current_app.config

    feed = AtomFeed(
        config['SITE_TITLE'],
        feed_url=request.url,
        url=request.url_root,
    )

    results, results_page = g.gitpages.index(
        1,
        ref=current_app.default_ref,
        statuses=g.allowed_statuses,
    )

    for page in results:

        doc = page.doc()

        utc_date = page.info.date.astimezone(pytz.utc)

        feed.add(
            doc['title'],
            doc['body'],
            content_type='html',
            url=urljoin(request.url_root, page.to_url()),
            updated=utc_date,
            published=utc_date,
        )

    return feed.get_response()


def rss_feed_redirect():
    return redirect(url_for('.atom_feed'), code=301)


def page_to_key(page):
    return page.info.blob_id


def page_by_path(path, statuses=None, template=None, context_overrides={}):

    try:

        page = g.gitpages.page_by_path(path)
        attachments = g.gitpages.attachments_by_path(path)
        return page_view(page, attachments, template, context_overrides)

    except (PageNotFound, AttachmentNotFound):

        raise NotFound()


def page_view(page, attachments=[], template=None, context_overrides={}):

    doc = page.doc()
    older = g.gitpages.older_pages(
        page,
        ref=page.info.ref,
        page_number=1,
        page_length=1,
        statuses=g.allowed_statuses,
    )
    newer = g.gitpages.newer_pages(
        page,
        ref=page.info.ref,
        page_number=1,
        page_length=1,
        statuses=g.allowed_statuses,
    )

    recent_pages = g.gitpages.recent_pages(
        page_number=1,
        page_length=10,
        statuses=g.allowed_statuses,
    )

    history = g.gitpages.history(
        page,
        page_number=1,
        statuses=g.allowed_statuses,
    )

    body = doc['body']
    title = doc['title']

    return render_template(
        template or 'page.html',
        title=title,
        body=body,
        page=page,
        attachments=attachments,
        page_prev=next(iter(older), None),
        page_next=next(iter(newer), None),
        page_history=history,
        recent_pages=recent_pages,
        **context_overrides
    )
