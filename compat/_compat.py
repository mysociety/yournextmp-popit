# -*- coding: utf-8 -*-

from __future__ import unicode_literals

from django.utils.encoding import python_2_unicode_compatible
import six
from six import text_type
from six.moves import input

import csv
import io

_ENCODING = 'utf-8'


def _map_dict(func, dict_):
    return {func(k): func(v) for k, v in dict_.items()}


class StreamDictReader(csv.DictReader):
    r"""A DictReader to work with streams, automating the selection of a buffer.

    Whereas the Python 2 ``csv`` module operates on binary files (and file-like
    objects), Python 3's is limited to Unicode.  ``StreamDictReader``
    requires both the input and output to be Unicode.

    >>> reader = StreamDictReader(u'α,b,c\r\n1,2,\r\n')
    >>> tuple(reader) == ({u'α': u'1', u'b': u'2', u'c': u''},)
    True
    """

    if six.PY2:
        def __init__(self, s='', fieldnames=None, restkey=None, restval=None,
                     dialect='excel', *_, **kwargs):
            s = io.BytesIO(unicode_to_bytes(s))
            csv.DictReader.__init__(
                self, s, fieldnames, restkey, restval, dialect,
                **_map_dict(unicode_to_bytes, kwargs))

        def next(self):
            return _map_dict(bytes_to_unicode, csv.DictReader.next(self))
    else:
        def __new__(cls, s='', fieldnames=None, restkey=None, restval=None,
                    dialect='excel', *_, **kwargs):
            s = io.StringIO(bytes_to_unicode(s))
            return csv.DictReader(s, fieldnames, restkey, restval, dialect,
                                  **kwargs)


class StreamDictWriter(csv.DictWriter):
    r"""A DictWriter to work with streams, automating the selection of a buffer.

    Whereas the Python 2 ``csv`` module operates on binary files (and file-like
    objects), Python 3's is limited to Unicode.  ``StreamDictWriter``
    requires both the input and output to be Unicode.

    >>> writer = StreamDictWriter((u'α', u'b', u'c'))
    >>> writer.writeheader()
    >>> _ = writer.writerow({u'α': 1, u'b': 2})
    >>> writer.output == u'α,b,c\r\n1,2,\r\n'
    True
    """

    if six.PY2:
        def __init__(self, fieldnames, restval='', extrasaction='raise',
                     dialect='excel', *_, **kwargs):
            self.f = io.BytesIO()
            csv.DictWriter.__init__(
                self, self.f, fieldnames, restval, extrasaction, dialect,
                **_map_dict(unicode_to_bytes, kwargs))

        def _dict_to_list(self, row_dict):
            return map(unicode_to_bytes,
                       csv.DictWriter._dict_to_list(self, row_dict))

        @property
        def output(self): return bytes_to_unicode(self.f.getvalue())
    else:
        def __init__(self, fieldnames, restval='', extrasaction='raise',
                     dialect='excel', *_, **kwargs):
            self.f = io.StringIO()
            super().__init__(self.f, fieldnames, restval, extrasaction,
                             dialect, **kwargs)

        @property
        def output(self): return self.f.getvalue()


def bytes_to_unicode(bytes_):
    """Convert ``bytes`` to Unicode in both Python 2 and 3."""
    if isinstance(bytes_, bytes):
        return bytes_.decode(_ENCODING)
    return bytes_


def unicode_to_bytes(unicode_):
    """Convert Unicode to ``bytes`` in both Python 2 and 3."""
    if isinstance(unicode_, text_type):
        return unicode_.encode(_ENCODING)
    return unicode_
