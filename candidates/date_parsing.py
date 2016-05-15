# -*- coding: utf-8 -*-

from collections import OrderedDict, namedtuple
import datetime as dt
import enum
import itertools as it
import re

from django.core.exceptions import ValidationError
from django.utils.translation import ugettext_lazy as _l
import icu

from compat import StrippedCharField

__all__ = ('DatePrecision', 'DateParser', 'Date', 'DateCharField')


class DatePrecision(enum.IntEnum):

    DAY = 0
    MONTH = 1
    YEAR = 2


class _cached_parser_property(object):

    def __init__(self, fn):
        self.fn_name = fn.__name__

    def __get__(self, _, owner):
        parser_instance = owner()
        # Replace the original ``DateParser.default_parser`` with our
        # ``parser_instance``
        setattr(owner, self.fn_name, parser_instance)
        return parser_instance


class DateParser(object):
    """A utility to parse short- and long-form date strings into date objects.

    ``DateParser`` converts user-submitted dates into Python ``datetime.date``
    objects.  It does this by generating localised date patterns and checking
    if any match the input.  ``DateParser`` also has limited support for
    partial dates.

        >>> dp = DateParser(locale='el')
        >>> date = dp.parse('Μάιος 2016')
        >>> date
        Date(date=datetime.date(2016, 5, 1), precision=<DatePrecision.MONTH: 1>)
        >>> str(date) == '2016-05'
        True

    ``DateParser`` won't parse any date that deviates from the canonical
    representations in the Unicode CLDR - with the exception of ISO 8601 -
    leaving little leeway for long dates.  Rather, ``DateParser`` and the
    accompanying ``DateCharField`` are optimised for the input of short
    dates.  The is because: (a) people are trained to abbreviate dates;
    and (b) long dates are complex and existing solutions are Anglocentric.
    """

    # The skeleton keys correspond to IDs in the Unicode CLDR
    _skeletons = OrderedDict(
        (('yMMMMd', DatePrecision.DAY),       # November
         ('yMMMd', DatePrecision.DAY),        # Nov
         ('yMd', DatePrecision.DAY),          # 12/12/12 and the like
         ('yMMMM', DatePrecision.MONTH),
         ('yMMM', DatePrecision.MONTH)))
    _patterns = OrderedDict(
        (('yyyy-MM-dd', DatePrecision.DAY),   # ISO 8601
         ('yyyy-MM', DatePrecision.MONTH),
         ('yyyy', DatePrecision.YEAR),
         ('LLLL y', DatePrecision.MONTH),     # Μάιος, cf. Μαΐου (see http://unicode.org/cldr/trac/ticket/8456)
         ('LLL y', DatePrecision.MONTH)))     # Μάι, cf. Μαΐ
    _skeletons_and_patterns = dict(it.chain(_skeletons.items(),
                                            _patterns.items()))

    # FIXME: there might be a way to accomplish this in ICU
    _validators = dict(it.chain(
        ((k, lambda v: v) for k in _skeletons_and_patterns),
        (('yyyy-MM-dd',
          lambda v, _r=re.compile(r'\d{4}-\d{2}-\d{2}$'): _r.match(v)),
         ('yyyy-MM',
          lambda v, _r=re.compile(r'\d{4}-\d{2}$'): _r.match(v)),
         ('yyyy',
          lambda v, _r=re.compile(r'\d{4}$'): _r.match(v)))))

    def _prepare(self, locale):
        locale = icu.Locale(locale)
        dtpg = icu.DateTimePatternGenerator.createInstance(locale)
        parsers = it.chain(((f, icu.SimpleDateFormat(dtpg.getBestPattern(f),
                                                     locale))
                            for f in self._skeletons),
                           ((f, icu.SimpleDateFormat(f, locale))
                            for f in self._patterns))
        parsers = OrderedDict(parsers)
        # Make sure dates are parsed reasonably strictly.  As of ICU 57.1,
        # the parse flags are:
        #   UDAT_PARSE_ALLOW_WHITESPACE = 0              | |
        #   UDAT_PARSE_ALLOW_NUMERIC = 1                 | |
        #   UDAT_PARSE_PARTIAL_LITERAL_MATCH = 2         |x|
        #   UDAT_PARSE_MULTIPLE_PATTERNS_FOR_MATCH = 3   |x|
        #   UDAT_BOOLEAN_ATTRIBUTE_COUNT = 4             |x|
        # However, for compatibility with older version of ICU, we're
        # only able to switch off the first two.
        for k in parsers:
            parsers[k].setLenient(False)
        return parsers, self._validators.copy()

    def __init__(self, locale=None):
        if not locale:
            from django.conf import settings
            locale = settings.LANGUAGE_CODE
        if locale == 'en':
            # Default to BrEng.  If you'd like for m/d/y, use
            # the 'en-us' locale
            locale = 'en-gb'
        self._locale = locale
        self._parser_fns, self._validators = self._prepare(locale)
        super(DateParser, self).__init__()

    @_cached_parser_property
    def default_parser():
        """A cached parser that's instantiated on first access."""

    def parse(self, initial_date):
        """Parse a date string into a ``Date`` object."""
        for parser in self._parser_fns:
            try:
                if not self._validators[parser](initial_date):
                    continue
                date = dt.date.fromtimestamp(self._parser_fns[parser]
                                             .parse(initial_date))
            except icu.ICUError:
                continue
            return Date(date, self._skeletons_and_patterns[parser])
        else:
            raise ValueError

    @property
    def canonical_short_date(self):
        """The canonical 'short' date in the ``self.locale``."""
        return self._parser_fns['yMd']


class Date(namedtuple('Date', 'date precision')):

    __slots__ = ()

    def __str__(self):
        """Convert to ISO and chop off the day and/or month if imprecise.

        Birth and death dates are copied into ``django-popolo``'s
        ``start_date`` and ``birth_date``, which require partial dates
        be in the form 'YYYY-MM' and 'YYYY'.  The actual birth and date
        fields have no such constraints and also differ in that they're not
        nullable.
        """
        date_string = self.date.isoformat()
        if self.precision is DatePrecision.MONTH:
            date_string, _, _  = date_string.rpartition('-')
        elif self.precision is DatePrecision.YEAR:
            date_string, _, _ = date_string.partition('-')
        return date_string


class DateCharField(StrippedCharField):

    default_error_messages = {
        'invalid': _l(u'The date could not be extracted from "{value}". '
                      u'Please try using a date like "{example}".')}

    def __init__(self, date_parser=None, **kwargs):
        self.date_parser = date_parser or DateParser.default_parser
        super(DateCharField, self).__init__(**kwargs)

    def get_prep_value(self, value):
        return str(value)

    def to_python(self, value):
        value = super(DateCharField, self).to_python(value)
        if not value:
            return value

        try:
            parsed = self.date_parser.parse(value)
        except ValueError:
            raise ValidationError(self.error_messages['invalid'].format(
                value=value,
                example=self.date_parser.canonical_short_date
                                        .format(dt.datetime.now())))
        return parsed
