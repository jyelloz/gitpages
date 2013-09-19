# -*- coding: utf-8 -*-

import re

from ..stolen import slugify, cached

__all__ = [
    'slugify',
    'cached',
    'inlineify',
]


_content_disposition_attachment_re = re.compile(
    # one time I misspelled 'attachment' as 'atachment'
    r'(att?achment)'
)


def inlineify(content_disposition_header):
    return _content_disposition_attachment_re.sub(
        'inline',
        content_disposition_header,
    )
