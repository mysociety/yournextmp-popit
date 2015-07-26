from mock import patch,  MagicMock
from datetime import date

import re

from django.conf import settings
from django.test.utils import override_settings
from django_webtest import WebTest

from .fake_popit import get_example_popit_json

fake_elections = {
    '2010': {
        'for_post_role': 'Member of Parliament',
        'election_date': date(2010, 8, 9),
        'candidacy_start_date': date(2010, 6, 22),
        'name': 'Fake 2010 election',
        'current': True,
        'party_membership_start_date': date(2010, 6, 22),
        'party_membership_end_date': date(9999, 12, 31),
        'mapit_types': ['WMC'],
        'mapit_generation': 22,
        'get_post_id': lambda mapit_type, area_id: str(area_id),
    },
    '2015': {
        'for_post_role': 'Member of Parliament',
        'election_date': date(2015, 8, 9),
        'candidacy_start_date': date(2015, 6, 22),
        'name': 'Fake 2015 election',
        'current': True,
        'use_for_candidate_suggestions': False,
        'party_membership_start_date': date(2015, 6, 22),
        'party_membership_end_date': date(9999, 12, 31),
        'mapit_types': ['WMC'],
        'mapit_generation': 22,
        'get_post_id': lambda mapit_type, area_id: str(area_id),
    }
}

current_fake_elections = sorted(
    fake_elections.items(),
    key=lambda e: (e[1]['election_date'], e[0]),
)


def fake_election_search_results(url, **kwargs):
    mock_requests_response = MagicMock()
    page = "1"
    m = re.search(r'[^_]page=(\d+)', url)
    if m:
        page = m.group(1)
    mock_requests_response.json.return_value = get_example_popit_json(
        'generic_posts_embed={0}.json'.format(page)
    )
    return mock_requests_response


def fake_post_search_results(url, **kwargs):
    mock_requests_response = MagicMock()
    mock_requests_response.json.return_value = get_example_popit_json(
        'generic_posts_embed=.json'
    )
    return mock_requests_response


class TestPostsView(WebTest):

    @patch('candidates.popit.requests')
    def test_single_election_posts_page(self, mock_requests):
        mock_requests.get.side_effect = fake_post_search_results

        response = self.app.get('/posts')

        self.assertTrue(
            response.html.find(
                'h2', text='2015 General Election'
            )
        )

        self.assertTrue(
            response.html.find(
                'a', text='Member of Parliament for Camberwell and Peckham'
            )
        )


    @override_settings(ELECTIONS_CURRENT=current_fake_elections)
    @patch('candidates.popit.requests')
    def test_two_elections_posts_page(self, mock_requests):
        mock_requests.get.side_effect = fake_post_search_results

        response = self.app.get('/posts')

        self.assertTrue(
            response.html.find(
                'h2', text='Fake 2010 election'
            )
        )

        self.assertTrue(
            response.html.find(
                'h2', text='Fake 2015 election'
            )
        )
