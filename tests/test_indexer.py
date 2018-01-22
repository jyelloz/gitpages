from gitpages import indexer

from whoosh.index import Index
from whoosh.fields import Schema

import pytest
import six


def test_when__directory_is_valid__then__makedirs_quiet_succeeds():
    indexer.makedirs_quiet('.')

def test_when__directory_is_invalid__then__makedirs_quiet_raises_oserror():
    with pytest.raises(OSError):
        indexer.makedirs_quiet('')


def test_when__directory_is_valid__then__get_index__creates_index(tmpdir):

    path = six.text_type(tmpdir.realpath())
    index = indexer.get_index(path, u'index', Schema())
    assert isinstance(index, Index)

def test_when__index_exists__then__get_index__returns_index(tmpdir):

    path = six.text_type(tmpdir.realpath())

    index = indexer.get_index(path, u'index', Schema())

    index = indexer.get_index(path, u'index', Schema())

    assert isinstance(index, Index)

def test_when__directory_is_invalid__then__get_index_raises_oserror():

    with pytest.raises(OSError):
        indexer.get_index('', 'index', Schema())
