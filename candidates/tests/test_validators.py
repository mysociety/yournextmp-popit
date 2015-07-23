from django.test import TestCase

from mock import patch

from ..forms import BasePersonForm, UpdatePersonForm

from candidates.tests.fake_popit import fake_mp_post_search_results

@patch('candidates.popit.PopIt')
@patch('candidates.popit.requests')
class TestValidators(TestCase):

    def test_twitter_bad_url(self, mock_requests, mock_popit):
        form = BasePersonForm({
            'name': 'John Doe',
            'twitter_username': 'http://example.org/blah',
        })
        self.assertFalse(form.is_valid())
        self.assertEqual(
            form.errors,
            {
                'twitter_username':
                [u'The Twitter username must only consist of alphanumeric characters or underscore']
            }
        )

    def test_twitter_fine(self, mock_requests, mock_popit):
        form = BasePersonForm({
            'name': 'John Doe',
            'twitter_username': 'madeuptwitteraccount',
        })
        self.assertTrue(form.is_valid())
        self.assertEqual(form.errors, {})
        self.assertEqual(
            form.cleaned_data['twitter_username'],
            'madeuptwitteraccount'
        )

    def test_twitter_full_url(self, mock_requests, mock_popit):
        form = BasePersonForm({
            'name': 'John Doe',
            'twitter_username': 'https://twitter.com/madeuptwitteraccount',
        })
        self.assertTrue(form.is_valid())
        self.assertEqual(form.errors, {})
        self.assertEqual(
            form.cleaned_data['twitter_username'],
            'madeuptwitteraccount'
        )

    def test_malformed_email(self, mock_requests, mock_popit):
        form = BasePersonForm({
            'name': 'John Bercow',
            'email': 'foo bar!',
        })
        self.assertFalse(form.is_valid())
        self.assertEqual(form.errors, {'email': ['Enter a valid email address.']})

    def test_update_person_form_standing_no_party_no_constituency(self, mock_requests, mock_popit):
        mock_requests.get.side_effect = fake_mp_post_search_results
        form = UpdatePersonForm({
            'name': 'John Doe',
            'source': 'Just testing...',
            'standing_2015': 'standing',
        })
        self.assertFalse(form.is_valid())
        self.assertEqual(form.errors, {
            '__all__':
            [u'If you mark the candidate as standing in the 2015 General Election, you must select a post']
        })

    def test_update_person_form_standing_no_party_but_gb_constituency(self, mock_requests, mock_popit):
        mock_requests.get.side_effect = fake_mp_post_search_results
        form = UpdatePersonForm({
            'name': 'John Doe',
            'source': 'Just testing...',
            'standing_2015': 'standing',
            'constituency_2015': '65808',
        })
        self.assertFalse(form.is_valid())
        self.assertEqual(form.errors, {
            '__all__':
            [u'You must specify a party for the 2015 General Election']
        })

    def test_update_person_form_standing_party_and_gb_constituency(self, mock_requests, mock_popit):
        mock_requests.get.side_effect = fake_mp_post_search_results
        form = UpdatePersonForm({
            'name': 'John Doe',
            'source': 'Just testing...',
            'standing_2015': 'standing',
            'constituency_2015': '65808',
            'party_gb_2015': 'party:52',
        })
        self.assertTrue(form.is_valid())

    # When 'not-standing' is selected, it shouldn't matter whether you
    # specify party of constituency:

    def test_update_person_form_not_standing_no_party_no_constituency(self, mock_requests, mock_popit):
        mock_requests.get.side_effect = fake_mp_post_search_results
        form = UpdatePersonForm({
            'name': 'John Doe',
            'source': 'Just testing...',
            'standing_2015': 'not-standing',
        })
        self.assertTrue(form.is_valid())

    def test_update_person_form_not_standing_no_party_but_gb_constituency(self, mock_requests, mock_popit):
        mock_requests.get.side_effect = fake_mp_post_search_results
        form = UpdatePersonForm({
            'name': 'John Doe',
            'source': 'Just testing...',
            'standing_2015': 'not-standing',
            'constituency_2015': '65808',
        })
        self.assertTrue(form.is_valid())

    def test_update_person_form_not_standing_party_and_gb_constituency(self, mock_requests, mock_popit):
        mock_requests.get.side_effect = fake_mp_post_search_results
        form = UpdatePersonForm({
            'name': 'John Doe',
            'source': 'Just testing...',
            'standing_2015': 'standing',
            'constituency_2015': '65808',
            'party_gb_2015': 'party:52',
        })
        self.assertTrue(form.is_valid())

    # Similarly, when 'not-sure' is selected, it shouldn't matter
    # whether you specify party of constituency:

    def test_update_person_form_not_sure_no_party_no_constituency(self, mock_requests, mock_popit):
        mock_requests.get.side_effect = fake_mp_post_search_results
        form = UpdatePersonForm({
            'name': 'John Doe',
            'source': 'Just testing...',
            'standing_2015': 'not-sure',
        })
        self.assertTrue(form.is_valid())

    def test_update_person_form_not_sure_no_party_but_gb_constituency(self, mock_requests, mock_popit):
        mock_requests.get.side_effect = fake_mp_post_search_results
        form = UpdatePersonForm({
            'name': 'John Doe',
            'source': 'Just testing...',
            'standing_2015': 'not-sure',
            'constituency_2015': '65808',
        })
        self.assertTrue(form.is_valid())

    def test_update_person_form_not_sure_party_and_gb_constituency(self, mock_requests, mock_popit):
        mock_requests.get.side_effect = fake_mp_post_search_results
        form = UpdatePersonForm({
            'name': 'John Doe',
            'source': 'Just testing...',
            'standing_2015': 'not-sure',
            'constituency_2015': '65808',
            'party_gb_2015': 'party:52',
        })
        self.assertTrue(form.is_valid())
