from mock import patch, MagicMock
import re

from django_webtest import WebTest

from .fake_popit import get_example_popit_json, FakeOrganizationCollection

from cached_counts.models import CachedCount

def fake_api_party_list(*args, **kwargs):
    page = kwargs.get('page')
    return get_example_popit_json(
        'organizations_embed=&page={0}&per_page=2.json'.format(page)
    )

def fake_party_person_search_results(url, **kwargs):
    mock_requests_response = MagicMock()
    page = "1"
    m = re.search(r'[^_]page=(\d+)', url)
    if m:
        page = m.group(1)
    mock_requests_response.json.return_value = get_example_popit_json(
        'search_labour_page={0}.json'.format(page)
    )
    return mock_requests_response


class TestPartyPages(WebTest):

    @classmethod
    def setUpClass(cls):
        cls.cached_counts = [
            CachedCount.objects.create(
                count_type='party',
                name='',
                count=count,
                object_id=object_id
            ) for object_id, count in (
                ('party:52', 4),
                ('party:63', 0),
                ('party:53', 5),
            )
        ]

    @classmethod
    def tearDownClass(cls):
        for cc in cls.cached_counts:
            cc.delete()

    @patch('candidates.popit.PopIt')
    def test_parties_page(self, mock_popit):
        mock_api = MagicMock()
        mock_api.organizations.get.side_effect = fake_api_party_list
        mock_popit.return_value = mock_api
        response = self.app.get('/election/2015/parties')
        ul = response.html.find('ul', {'class': 'party-list'})
        lis = ul.find_all('li')
        self.assertEqual(len(lis), 2)
        for i, t in enumerate((
            ('/election/2015/party/party:52/conservative-party', 'Conservative Party'),
            ('/election/2015/party/party:53/labour-party', 'Labour Party'),
        )):
            expected_url = t[0]
            expected_text = t[1]
            self.assertEqual(lis[i].find('a')['href'], expected_url)
            self.assertEqual(lis[i].find('a').text, expected_text)

    @patch('candidates.views.parties.requests')
    @patch('candidates.popit.PopIt')
    def test_single_party_page(self, mock_popit, mock_requests):
        mock_popit.return_value.organizations = FakeOrganizationCollection
        mock_requests.get.side_effect = fake_party_person_search_results
        response = self.app.get('/election/2015/party/party%3A53/labour-party')
        # There are no candidates in Scotland or Wales in our test data:
        self.assertIn(
            u"We don't know of any Labour Party candidates in Scotland so far.",
            unicode(response)
        )
        self.assertIn(
            u"We don't know of any Labour Party candidates in Wales so far.",
            unicode(response)
        )
        # But this should only be showing results from the Great
        # Britain register, so there shouldn't be a similar message
        # for Northern Ireland:
        self.assertNotIn(
            u"We don't know of any Labour Party candidates in Northern Ireland so far.",
            unicode(response)
        )
        # Check there's no mention of David Miliband's constituency
        # (since he's not standing in 2015) and we've not added enough
        # example candidates to reach the threshold where all
        # constituencies should be shown:
        self.assertNotIn(
            u'South Shields',
            unicode(response)
        )
        # But there is an Ed Miliband:
        self.assertTrue(re.search(
            r'(?ms)<a href="/person/3056">Ed Miliband</a>.*is standing in.*' +
            r'<a href="/election/2015/post/65672/doncaster-north">Doncaster North</a></li>',
            unicode(response)
        ))
