from __future__ import unicode_literals

from datetime import date
from mock import patch

from django.test import TestCase

from candidates.models import PersonExtra
from popolo.models import Person

@patch('candidates.models.popolo_extra.date')
class TestAgeCalculation(TestCase):

    def test_age_full_obvious(self, mock_date):
        mock_date.today.return_value = date(1977, 9, 3)
        mock_date.side_effect = \
            lambda *args, **kwargs: date(*args, **kwargs)
        p = Person.objects.create(
            name='Test Person',
            birth_date='1976-09-01'
        )
        pe = PersonExtra.objects.create(base=p)
        self.assertEqual(p.extra.age, '1')

    def test_age_full_early_in_year(self, mock_date):
        mock_date.today.return_value = date(1977, 2, 28)
        mock_date.side_effect = \
            lambda *args, **kwargs: date(*args, **kwargs)
        p = Person.objects.create(
            name='Test Person',
            birth_date='1976-09-01'
        )
        pe = PersonExtra.objects.create(base=p)
        self.assertEqual(p.extra.age, '0')

    def test_age_month_obvious(self, mock_date):
        mock_date.today.return_value = date(1977, 10, 3)
        mock_date.side_effect = \
            lambda *args, **kwargs: date(*args, **kwargs)
        p = Person.objects.create(
            name='Test Person',
            birth_date='1976-09'
        )
        pe = PersonExtra.objects.create(base=p)
        self.assertEqual(p.extra.age, '1')

    def test_age_month_early_in_year(self, mock_date):
        mock_date.today.return_value = date(1977, 8, 15)
        mock_date.side_effect = \
            lambda *args, **kwargs: date(*args, **kwargs)
        p = Person.objects.create(
            name='Test Person',
            birth_date='1976-09'
        )
        pe = PersonExtra.objects.create(base=p)
        self.assertEqual(p.extra.age, '0')

    def test_age_month_ambiguous(self, mock_date):
        mock_date.today.return_value = date(1977, 9, 10)
        mock_date.side_effect = \
            lambda *args, **kwargs: date(*args, **kwargs)
        p = Person.objects.create(
            name='Test Person',
            birth_date='1976-09'
        )
        pe = PersonExtra.objects.create(base=p)
        self.assertEqual(p.extra.age, '0 or 1')

    def test_age_year_ambiguous(self, mock_date):
        mock_date.today.return_value = date(1977, 9, 10)
        mock_date.side_effect = \
            lambda *args, **kwargs: date(*args, **kwargs)
        p = Person.objects.create(
            name='Test Person',
            birth_date='1975'
        )
        pe = PersonExtra.objects.create(base=p)
        self.assertEqual(p.extra.age, '1 or 2')
