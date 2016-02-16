from __future__ import unicode_literals

from django_webtest import WebTest

from .factories import (
    AreaExtraFactory, AreaTypeFactory, ElectionFactory,
    PostExtraFactory, ParliamentaryChamberExtraFactory,
    PersonExtraFactory, CandidacyExtraFactory, PartyExtraFactory,
    PartyFactory, MembershipFactory, PartySetFactory
)

from candidates.models import LoggedAction


class TestAPI(WebTest):

    def setUp(self):
        wmc_area_type = AreaTypeFactory.create()
        gb_parties = PartySetFactory.create(slug='gb', name='Great Britain')
        commons = ParliamentaryChamberExtraFactory.create()

        self.election = ElectionFactory.create(
            slug='2015',
            name='2015 General Election',
            area_types=(wmc_area_type,),
            organization=commons.base
        )
        old_election = ElectionFactory.create(
            slug='2010',
            name='2010 General Election',
            area_types=(wmc_area_type,),
            organization=commons.base
        )

        PartyFactory.reset_sequence()
        PartyExtraFactory.reset_sequence()
        party_extra = PartyExtraFactory.create()
        gb_parties.parties.add(party_extra.base)

        dulwich_area_extra = AreaExtraFactory.create(
            base__identifier='65808',
            base__name='Dulwich and West Norwood',
            type=wmc_area_type,
        )

        post_extra = PostExtraFactory.create(
            elections=(self.election,),
            base__organization=commons.base,
            base__area=dulwich_area_extra.base,
            slug='65808',
            base__label='Member of Parliament for Dulwich and West Norwood',
            party_set=gb_parties,
        )
        winner_post_extra = PostExtraFactory.create(
            elections=(self.election,),
            base__organization=commons.base,
            slug='14419',
            base__label='Member of Parliament for Edinburgh East',
            party_set=gb_parties,
        )

        person_extra = PersonExtraFactory.create(
            base__id='2009',
            base__name='Tessa Jowell'
        )
        dulwich_not_stand = PersonExtraFactory.create(
            base__id='4322',
            base__name='Helen Hayes'
        )
        edinburgh_candidate = PersonExtraFactory.create(
            base__id='818',
            base__name='Sheila Gilmore'
        )
        edinburgh_winner = PersonExtraFactory.create(
            base__id='5795',
            base__name='Tommy Sheppard'
        )
        edinburgh_may_stand = PersonExtraFactory.create(
            base__id='5163',
            base__name='Peter McColl'
        )

        CandidacyExtraFactory.create(
            election=self.election,
            base__person=person_extra.base,
            base__post=post_extra.base,
            base__on_behalf_of=party_extra.base
            )
        MembershipFactory.create(
            person=person_extra.base,
            organization=party_extra.base
        )

        CandidacyExtraFactory.create(
            election=old_election,
            base__person=dulwich_not_stand.base,
            base__post=post_extra.base,
            base__on_behalf_of=party_extra.base,
            )
        dulwich_not_stand.not_standing.add(self.election)

        CandidacyExtraFactory.create(
            election=self.election,
            base__person=edinburgh_winner.base,
            base__post=winner_post_extra.base,
            base__on_behalf_of=party_extra.base,
            elected=True,
            )

        CandidacyExtraFactory.create(
            election=self.election,
            base__person=edinburgh_candidate.base,
            base__post=winner_post_extra.base,
            base__on_behalf_of=party_extra.base
            )
        MembershipFactory.create(
            person=edinburgh_candidate.base,
            organization=party_extra.base
        )

        MembershipFactory.create(
            person=edinburgh_winner.base,
            organization=party_extra.base
        )
        CandidacyExtraFactory.create(
            election=old_election,
            base__person=edinburgh_may_stand.base,
            base__post=winner_post_extra.base,
            base__on_behalf_of=party_extra.base
            )

    def test_api_basic_response(self):
        response = self.app.get(
            '/api/v0.9/'
        )
        self.assertEqual(response.status_code, 200)
        json = response.json

        self.assertEqual(
            json['persons'],
            'http://localhost:80/api/v0.9/persons/'
        )
        self.assertEqual(json['areas'], 'http://localhost:80/api/v0.9/areas/')
        self.assertEqual(
            json['organizations'],
            'http://localhost:80/api/v0.9/organizations/'
        )
        self.assertEqual(
            json['elections'],
            'http://localhost:80/api/v0.9/elections/'
        )
        self.assertEqual(json['posts'], 'http://localhost:80/api/v0.9/posts/')

        persons_resp = self.app.get('/api/v0.9/persons/')
        self.assertEqual(persons_resp.status_code, 200)

        areas_resp = self.app.get('/api/v0.9/areas/')
        self.assertEqual(areas_resp.status_code, 200)

        organizations_resp = self.app.get('/api/v0.9/organizations/')
        self.assertEqual(organizations_resp.status_code, 200)

        elections_resp = self.app.get('/api/v0.9/elections/')
        self.assertEqual(elections_resp.status_code, 200)

        posts_resp = self.app.get('/api/v0.9/posts/')
        self.assertEqual(posts_resp.status_code, 200)

    def test_api_errors(self):
        response = self.app.get(
            '/api/',
            expect_errors=True
        )
        self.assertEqual(response.status_code, 404)

        response = self.app.get(
            '/api/v0.8',
            expect_errors=True
        )
        self.assertEqual(response.status_code, 404)

        response = self.app.get(
            '/api/v0.9/person/',
            expect_errors=True
        )
        self.assertEqual(response.status_code, 404)

        response = self.app.get(
            '/api/v0.9/persons/4000/',
            expect_errors=True
        )
        self.assertEqual(response.status_code, 404)

        response = self.app.post(
            '/api/v0.9/persons/',
            {},
            expect_errors=True
        )
        self.assertEqual(response.status_code, 403)

    def test_api_persons(self):
        persons_resp = self.app.get('/api/v0.9/persons/')

        persons = persons_resp.json

        self.assertEqual(persons['count'], len(persons['results']))
        self.assertEqual(persons['count'], 5)

    def test_api_person(self):
        person_resp = self.app.get('/api/v0.9/persons/2009/')

        self.assertEqual(person_resp.status_code, 200)

        person = person_resp.json
        self.assertEqual(person['id'], 2009)
        self.assertEqual(person['name'], 'Tessa Jowell')

        memberships = person['memberships']

        self.assertEqual(len(memberships), 2)
        self.assertEqual(memberships[1]['role'], 'Candidate')

        self.assertEqual(len(person['versions']), 0)

    def test_api_areas(self):
        areas_resp = self.app.get('/api/v0.9/areas/')

        areas = areas_resp.json

        self.assertEqual(areas['count'], len(areas['results']))
        self.assertEqual(areas['count'], 1)

    def test_api_area(self):
        areas_resp = self.app.get('/api/v0.9/areas/')
        areas = areas_resp.json

        area_id = 0
        for area in areas['results']:
            if area['identifier'] == '65808':
                area_id = area['id']
                break

        area_url = '/api/v0.9/areas/{0}/'.format(area_id)
        area_resp = self.app.get(area_url)
        self.assertEqual(area_resp.status_code, 200)

        area = area_resp.json
        self.assertEqual(area['identifier'], '65808')
        self.assertEqual(area['name'], 'Dulwich and West Norwood')
        self.assertEqual(area['type']['name'], 'WMC')

    def test_api_organizations(self):
        organizations_resp = self.app.get('/api/v0.9/organizations/')

        organizations = organizations_resp.json

        self.assertEqual(organizations['count'], len(organizations['results']))
        self.assertEqual(organizations['count'], 2)

    def test_api_organization(self):
        organizations_resp = self.app.get('/api/v0.9/organizations/')
        organizations = organizations_resp.json

        organization_url = None
        for organization in organizations['results']:
            if organization['id'] == 'party:53':
                organization_url = organization['url']
                break

        organization_resp = self.app.get(organization_url)
        self.assertEqual(organization_resp.status_code, 200)

        organization = organization_resp.json
        self.assertEqual(organization['id'], 'party:53')
        self.assertEqual(organization['name'], 'Labour Party')

    def test_api_elections(self):
        elections_resp = self.app.get('/api/v0.9/elections/')

        elections = elections_resp.json

        self.assertEqual(elections['count'], len(elections['results']))
        self.assertEqual(elections['count'], 2)

    def test_api_election(self):
        elections_resp = self.app.get('/api/v0.9/elections/')
        elections = elections_resp.json

        election_url = None
        for election in elections['results']:
            if election['id'] == '2015':
                election_url = election['url']
                break

        election_resp = self.app.get(election_url)
        self.assertEqual(election_resp.status_code, 200)

        election = election_resp.json
        self.assertEqual(election['id'], '2015')
        self.assertEqual(election['name'], '2015 General Election')

    def test_api_posts(self):
        posts_resp = self.app.get('/api/v0.9/posts/')

        posts = posts_resp.json

        self.assertEqual(posts['count'], len(posts['results']))
        self.assertEqual(posts['count'], 2)

    def test_api_post(self):
        posts_resp = self.app.get('/api/v0.9/posts/')
        posts = posts_resp.json

        post_url = None
        for post in posts['results']:
            if post['id'] == '65808':
                post_url = post['url']
                break

        self.assertTrue(post_url)
        post_resp = self.app.get(post_url)
        self.assertEqual(post_resp.status_code, 200)

        post = post_resp.json

        self.assertEqual(post['id'], '65808')
        self.assertEqual(
            post['label'],
            'Member of Parliament for Dulwich and West Norwood'
        )

    def test_api_version_info(self):
        version_resp = self.app.get('/version.json')
        self.assertEqual(version_resp.status_code, 200)

        info = version_resp.json
        self.assertEqual(info['users_who_have_edited'], 0)
        self.assertEqual(info['interesting_user_actions'], 0)

        LoggedAction.objects.create(
            action_type='set-candidate-not-elected'
        )

        LoggedAction.objects.create(
            action_type='edit-candidate'
        )

        version_resp = self.app.get('/version.json')
        info = version_resp.json
        self.assertEqual(info['interesting_user_actions'], 1)

    def test_api_cors_headers(self):
        resp = self.app.get('/api/v0.9/', headers={
            'Origin': b'http://example.com'}
        )
        self.assertTrue('Access-Control-Allow-Origin' in resp.headers)
        self.assertEqual(resp.headers['Access-Control-Allow-Origin'], '*')

        resp = self.app.get('/', headers={
            'Origin': b'http://example.com'}
        )
        self.assertFalse('Access-Control-Allow-Origin' in resp.headers)
