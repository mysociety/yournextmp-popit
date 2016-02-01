from __future__ import unicode_literals

from django.test import TestCase
from django.test.utils import override_settings

from django.utils.translation import override

from django_date_extensions.fields import ApproximateDate

from candidates.models import parse_approximate_date

# These tests supplement the doctests; they're not done as
# doctests because we need to override settings to pick
# either US or non-US day/month default ordering:

class DateParsingTests(TestCase):

    def test_only_year(self):
        parsed = parse_approximate_date('1977')
        self.assertEqual(type(parsed), ApproximateDate)
        self.assertEqual(repr(parsed), '1977-00-00')

    def test_iso_8601(self):
        parsed = parse_approximate_date('1977-04-01')
        self.assertEqual(type(parsed), ApproximateDate)
        self.assertEqual(repr(parsed), '1977-04-01')

    def test_nonsense(self):
        with self.assertRaises(ValueError):
            parse_approximate_date('12345678')

    def test_dd_mm_yyyy_with_slashes(self):
        parsed = parse_approximate_date('1/4/1977')
        self.assertEqual(type(parsed), ApproximateDate)
        self.assertEqual(repr(parsed), '1977-04-01')

    @override_settings(DD_MM_DATE_FORMAT_PREFERRED=False)
    def test_mm_dd_yyyy_with_slashes(self):
        parsed = parse_approximate_date('4/1/1977')
        self.assertEqual(type(parsed), ApproximateDate)
        self.assertEqual(repr(parsed), '1977-04-01')

    def test_dd_mm_yyyy_with_dashes(self):
        parsed = parse_approximate_date('1-4-1977')
        self.assertEqual(type(parsed), ApproximateDate)
        self.assertEqual(repr(parsed), '1977-04-01')

    def test_natural_date_string(self):
        parsed = parse_approximate_date('31st December 1999')
        self.assertEqual(type(parsed), ApproximateDate)
        self.assertEqual(repr(parsed), '1999-12-31')

    def test_empty_string(self):
        with self.assertRaises(ValueError):
            parse_approximate_date('')

    def test_expanded_natural_date_string(self):
        parsed = parse_approximate_date('31st of December 1999')
        self.assertEqual(type(parsed), ApproximateDate)
        self.assertEqual(repr(parsed), '1999-12-31')

    def test_nonsense_string(self):
        with self.assertRaises(ValueError):
            parse_approximate_date('this is not a date')

    def test_spanish_date_string(self):
        with self.assertRaises(ValueError):
            parsed = parse_approximate_date('20 febrero 1954 ')
        with override('es'):
            parsed = parse_approximate_date('20 febrero 1954 ')
            self.assertEqual(type(parsed), ApproximateDate)
            self.assertEqual(repr(parsed), '1954-02-20')
