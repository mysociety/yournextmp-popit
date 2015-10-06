# -*- coding: utf-8 -*-

from mock import patch, Mock

from urlparse import urlsplit

from django_webtest import WebTest

from .fake_popit import FakePostCollection

def fake_requests_for_mapit(url):
    """Return reduced MapIt output for some known URLs"""
    if url == 'http://mapit.mysociety.org/postcode/sw1a1aa':
        status_code = 200
        json_result = {
            "shortcuts": {
                "WMC": 65759,
            },
        }
    elif url == 'http://mapit.mysociety.org/postcode/se240ag':
        status_code = 200
        json_result = {
            "shortcuts": {
                "WMC": "65808",
            },
        }
    elif url == 'http://mapit.mysociety.org/postcode/cb28rq':
        status_code = 404
        json_result = {
            "code": 404,
            "error": "No Postcode matches the given query."
        }
    elif url == 'http://mapit.mysociety.org/postcode/foobar':
        status_code = 400
        json_result = {
            "code": 400,
            "error": "Postcode 'FOOBAR' is not valid."
        }
    else:
        raise Exception("URL that hasn't been mocked yet: " + url)
    return Mock(**{
        'json.return_value': json_result,
        'status_code': status_code
    })

@patch('candidates.popit.PopIt')
@patch('elections.uk_general_election_2015.mapit.requests')
class TestConstituencyPostcodeFinderView(WebTest):

    def test_front_page(self, mock_requests, mock_popit):
        response = self.app.get('/')
        # Check that there is a form on that page
        response.forms['form-postcode']
        response.forms['form-name']

    def test_valid_postcode_redirects_to_constituency(self, mock_requests, mock_popit):
        mock_requests.get.side_effect = fake_requests_for_mapit
        mock_popit.return_value.posts = FakePostCollection
        response = self.app.get('/')
        form = response.forms['form-postcode']
        form['postcode'] = 'SE24 0AG'
        response = form.submit()
        self.assertEqual(response.status_code, 302)
        split_location = urlsplit(response.location)
        self.assertEqual(
            split_location.path,
            '/election/2015/post/65808/dulwich-and-west-norwood',
        )

    def test_unknown_postcode_returns_to_finder_with_error(self, mock_requests, mock_popit):
        mock_requests.get.side_effect = fake_requests_for_mapit
        response = self.app.get('/')
        form = response.forms['form-postcode']
        # This looks like a postcode to the usual postcode-checking
        # regular expressions, but doesn't actually exist
        form['postcode'] = 'CB2 8RQ'
        response = form.submit()
        self.assertEqual(response.status_code, 200)
        self.assertIn('The postcode “CB2 8RQ” couldn’t be found', response)

    def test_nonsense_postcode_returns_to_finder_with_error(self, mock_requests, mock_popit):
        mock_requests.get.side_effect = fake_requests_for_mapit
        response = self.app.get('/')
        form = response.forms['form-postcode']
        # This looks like a postcode to the usual postcode-checking
        # regular expressions, but doesn't actually exist
        form['postcode'] = 'foo bar'
        response = form.submit()
        self.assertEqual(response.status_code, 200)
        self.assertIn('Postcode &#39;FOOBAR&#39; is not valid.', response)

    def test_nonascii_postcode(self, mock_requests, mock_popit):
        mock_requests.get.side_effect = fake_requests_for_mapit
        response = self.app.get('/')
        form = response.forms['form-postcode']
        # Postcodes with non-ASCII characters should be rejected
        form['postcode'] = u'SW1A 1ӔA'
        response = form.submit()
        self.assertEqual(response.status_code, 200)
        self.assertIn(
            u'There were disallowed characters in &quot;SW1A 1ӔA&quot;',
            response
        )


@patch('candidates.popit.PopIt')
class TestConstituencyNameFinderView(WebTest):

    def test_pick_constituency_name(self, mock_popit):
        mock_popit.return_value.posts = FakePostCollection
        response = self.app.get('/')
        form = response.forms['form-name']
        form['constituency'] = '65808'
        response = form.submit()
        self.assertEqual(response.status_code, 302)
        split_location = urlsplit(response.location)
        self.assertEqual(
            split_location.path,
            '/election/2015/post/65808/dulwich-and-west-norwood'
        )

    def test_post_no_constituency_selected(self, mock_popit):
        response = self.app.get('/')
        form = response.forms['form-name']
        form['constituency'] = 'none'
        response = form.submit()
        self.assertEqual(response.status_code, 200)
        self.assertIn('You must select a constituency', response)

    def test_post_invalid_constituency_id(self, mock_popit):
        response = self.app.post(
            '/lookup/name',
            {
                'constituency': 'made-up-555',
            }
        )
        self.assertIn(
            'Select a valid choice. made-up-555 is not one of the available choices.',
            response
        )
