from __future__ import print_function, unicode_literals

import difflib
import json

import sys

from compat import text_type

def p(*args):
    """A helper for printing to stderr"""
    print(file=sys.stderr, *args)

def deep_cast_to_unicode(obj):
    """
    >>> deep_cast_to_unicode(b'Foo') == u'Foo'
    True
    >>> deep_cast_to_unicode({b'x': b'y'}) == {u'x': u'y'}
    True
    >>> (deep_cast_to_unicode([b'a', b'b', u'c', {b'x': b'y'}]) ==
         [u'a', u'b', u'c', {u'x': u'y'}])
    True
    """
    if isinstance(obj, text_type):
        return obj
    elif isinstance(obj, bytes):
        return obj.decode('utf-8')
    elif isinstance(obj, dict):
        return {deep_cast_to_unicode(k): deep_cast_to_unicode(v)
                for k, v in obj.items()}
    elif isinstance(obj, list):
        return [deep_cast_to_unicode(k) for k in obj]
    elif obj is None:
        return None
    return repr(obj)

def equal_arg(arg1, arg2):
    """Return True if the args are equal, False otherwise

    If the arguments aren't equal under ==, return True, otherwise
    return False and try to output to stderr a diff of the
    pretty-printed objects."""

    if arg1 == arg2:
        return True

    # This is more or less taken from assertDictEqual in
    # django/utils/unittest/case.py:
    args1_lines = json.dumps(deep_cast_to_unicode(arg1), indent=4,
                             sort_keys=True).splitlines()
    args2_lines = json.dumps(deep_cast_to_unicode(arg2), indent=4,
                             sort_keys=True).splitlines()
    diff = difflib.ndiff(args1_lines, args2_lines)

    p("Found the following differences: ====================================")
    for line in diff:
        p(line)
    p("=====================================================================")

    return False

def equal_call_args(args1, args2):
    """Return True if two sequences of arguments are equal

    Otherwise return False and output a diff of the first non-equal
    arguments to stderr."""
    if len(args1) != len(args2):
        message = "The argument lists were different lengths: {0} and {1}"
        p(message.format(len(args1), len(args2)))

    for i, arg1 in enumerate(args1):
        if not equal_arg(arg1, args2[i]):
            return False

    return True
