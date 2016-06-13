# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.test import TestCase
from django.test.utils import override_settings

from ..date_parsing import Date, DateParser

# These tests supplement the doctests; they're not done as
# doctests because we need to override settings to pick
# either US or non-US day/month default ordering:

class DateParsingTests(TestCase):

    def setUp(self):
        import icu
        self.icu_version = tuple(map(int, icu.ICU_VERSION.split('.')))

    def test_only_year(self):
        parsed = DateParser.default_parser.parse('1977')
        self.assertIsInstance(parsed, Date)
        self.assertEqual(str(parsed), '1977')

    def test_iso_8601(self):
        parsed = DateParser.default_parser.parse('1977-04-01')
        self.assertEqual(str(parsed), '1977-04-01')

    def test_nonsense(self):
        with self.assertRaises(ValueError):
            DateParser.default_parser.parse('12345678')

    def test_dd_mm_yyyy_with_slashes(self):
        parsed = DateParser.default_parser.parse('1/4/1977')
        self.assertEqual(str(parsed), '1977-04-01')

    @override_settings(LANGUAGE_CODE='en-us')
    def test_mm_dd_yyyy_with_slashes(self):
        parsed = DateParser().parse('4/1/1977')
        self.assertEqual(str(parsed), '1977-04-01')

    def test_dd_mm_yyyy_with_dashes(self):
        parsed = DateParser.default_parser.parse('1-4-1977')
        self.assertEqual(str(parsed), '1977-04-01')

    def test_natural_date_string(self):
        parsed = DateParser.default_parser.parse('31 December 1999')
        self.assertEqual(str(parsed), '1999-12-31')

    def test_abbreviated_month(self):
        parsed = DateParser.default_parser.parse('31 Dec 1999')
        self.assertEqual(str(parsed), '1999-12-31')

    def test_empty_string(self):
        with self.assertRaises(ValueError):
            DateParser.default_parser.parse('')

    def test_ordinals_and_preps(self):
        with self.assertRaises(ValueError):
            DateParser.default_parser.parse('31st of December 1999')

    def test_nonsense_string(self):
        with self.assertRaises(ValueError):
            DateParser.default_parser.parse('this is not a date')

    def test_spanish_date_string(self):
        with self.assertRaises(ValueError):
            DateParser.default_parser.parse('20 febrero 1954 ')
        dp = DateParser('es')
        parsed = dp.parse('20 febrero 1954 ')
        self.assertEqual(str(parsed), '1954-02-20')
        parsed = dp.parse('20 de febrero de 1954 ')
        self.assertEqual(str(parsed), '1954-02-20')

    def test_suggested_date(self):
        suggested_date = DateParser.default_parser.canonical_short_date
        if self.icu_version <= (21, 0, 1):
            self.assertEqual(suggested_date.toPattern(), 'd/M/yyyy')
        elif self.icu_version == (22, 1):
            self.assertEqual(suggested_date.toPattern(), 'dd/MM/yyyy')
        else:
            self.assertEqual(suggested_date.toPattern(), 'dd/MM/y')

        with override_settings(LANGUAGE_CODE='tr'):
            suggested_date = DateParser().canonical_short_date
            if self.icu_version <= (22, 1):
                self.assertEqual(suggested_date.toPattern(), 'dd.MM.yyyy')
            else:
                self.assertEqual(suggested_date.toPattern(), 'dd.MM.y')

    @override_settings(LANGUAGE_CODE='el')
    def test_all_greek(self):
        dp = DateParser()
        parsed = dp.parse('20 Φεβρουαρίου 1954')
        self.assertEqual(str(parsed), '1954-02-20')
        parsed = dp.parse('Φεβρουάριος 1954')
        self.assertEqual(str(parsed), '1954-02')
        parsed = dp.parse('20/02/1954')
        self.assertEqual(str(parsed), '1954-02-20')
        parsed = dp.parse('20/2/1954')
        self.assertEqual(str(parsed), '1954-02-20')
        parsed = dp.parse('20-2-1954')
        self.assertEqual(str(parsed), '1954-02-20')
        parsed = dp.parse('1954-02-20')
        self.assertEqual(str(parsed), '1954-02-20')
        parsed = dp.parse('1954-02')
        self.assertEqual(str(parsed), '1954-02')
        parsed = dp.parse('1954')
        self.assertEqual(str(parsed), '1954')
