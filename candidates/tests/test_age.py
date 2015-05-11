from datetime import date
from mock import patch

from django.test import TestCase

from candidates.models import PopItPerson

@patch('candidates.models.popit.date')
class TestAgeCalculation(TestCase):

    def test_age_full_obvious(self, mock_date):
        mock_date.today.return_value = date(1977, 9, 3)
        mock_date.side_effect = \
            lambda *args, **kwargs: date(*args, **kwargs)
        p = PopItPerson.create_from_dict({'birth_date': '1976-09-01'})
        self.assertEqual(p.age, '1')

    def test_age_full_early_in_year(self, mock_date):
        mock_date.today.return_value = date(1977, 2, 28)
        mock_date.side_effect = \
            lambda *args, **kwargs: date(*args, **kwargs)
        p = PopItPerson.create_from_dict({'birth_date': '1976-09-01'})
        self.assertEqual(p.age, '0')

    def test_age_month_obvious(self, mock_date):
        mock_date.today.return_value = date(1977, 10, 3)
        mock_date.side_effect = \
            lambda *args, **kwargs: date(*args, **kwargs)
        p = PopItPerson.create_from_dict({'birth_date': '1976-09'})
        self.assertEqual(p.age, '1')

    def test_age_month_early_in_year(self, mock_date):
        mock_date.today.return_value = date(1977, 8, 15)
        mock_date.side_effect = \
            lambda *args, **kwargs: date(*args, **kwargs)
        p = PopItPerson.create_from_dict({'birth_date': '1976-09'})
        self.assertEqual(p.age, '0')

    def test_age_month_ambiguous(self, mock_date):
        mock_date.today.return_value = date(1977, 9, 10)
        mock_date.side_effect = \
            lambda *args, **kwargs: date(*args, **kwargs)
        p = PopItPerson.create_from_dict({'birth_date': '1976-09'})
        self.assertEqual(p.age, '0 or 1')

    def test_age_year_ambiguous(self, mock_date):
        mock_date.today.return_value = date(1977, 9, 10)
        mock_date.side_effect = \
            lambda *args, **kwargs: date(*args, **kwargs)
        p = PopItPerson.create_from_dict({'birth_date': '1975'})
        self.assertEqual(p.age, '1 or 2')
