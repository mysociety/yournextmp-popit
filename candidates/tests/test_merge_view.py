from __future__ import unicode_literals

from mock import patch

from django.db.models import F

from django_webtest import WebTest

from popolo.models import Person

from candidates.models import PersonRedirect, MembershipExtra
from .auth import TestUserMixin
from . import factories

example_timestamp = '2014-09-29T10:11:59.216159'
example_version_id = '5aa6418325c1a0bb'


class TestMergePeopleView(TestUserMixin, WebTest):

    def setUp(self):
        # FIXME: essentially repeated from test_revert.py, should
        # factor out this duplication.
        wmc_area_type = factories.AreaTypeFactory.create()
        gb_parties = factories.PartySetFactory.create(
            slug='gb', name='Great Britain'
        )
        election = factories.ElectionFactory.create(
            slug='2015',
            name='2015 General Election',
            area_types=(wmc_area_type,)
        )
        earlier_election = factories.EarlierElectionFactory.create(
            slug='2010',
            name='2010 General Election',
            area_types=(wmc_area_type,)
        )
        commons = factories.ParliamentaryChamberFactory.create()
        post_extra = factories.PostExtraFactory.create(
            elections=(election, earlier_election),
            base__organization=commons,
            slug='65808',
            base__label='Member of Parliament for Dulwich and West Norwood',
            party_set=gb_parties,
        )
        # Create Tessa Jowell (the primary person)
        person_extra = factories.PersonExtraFactory.create(
            base__id=2009,
            base__name='Tessa Jowell',
            base__gender='female',
            base__honorific_suffix='DBE',
            base__email='jowell@example.com',
            versions='''
                [
                  {
                    "username": "symroe",
                    "information_source": "Just adding example data",
                    "ip": "127.0.0.1",
                    "version_id": "35ec2d5821176ccc",
                    "timestamp": "2014-10-28T14:32:36.835429",
                    "data": {
                      "name": "Tessa Jowell",
                      "id": "2009",
                      "honorific_suffix": "DBE",
                      "twitter_username": "",
                      "standing_in": {
                        "2010": {
                          "post_id": "65808",
                          "name": "Dulwich and West Norwood",
                          "mapit_url": "http://mapit.mysociety.org/area/65808"
                        },
                        "2015": {
                          "post_id": "65808",
                          "name": "Dulwich and West Norwood",
                          "mapit_url": "http://mapit.mysociety.org/area/65808"
                        }
                      },
                      "gender": "female",
                      "homepage_url": "",
                      "birth_date": null,
                      "wikipedia_url": "https://en.wikipedia.org/wiki/Tessa_Jowell",
                      "party_memberships": {
                        "2010": {
                          "id": "party:53",
                          "name": "Labour Party"
                        },
                        "2015": {
                          "id": "party:53",
                          "name": "Labour Party"
                        }
                      },
                      "email": "jowell@example.com"
                    }
                  },
                  {
                    "username": "mark",
                    "information_source": "An initial version",
                    "ip": "127.0.0.1",
                    "version_id": "5469de7db0cbd155",
                    "timestamp": "2014-10-01T15:12:34.732426",
                    "data": {
                      "name": "Tessa Jowell",
                      "id": "2009",
                      "twitter_username": "",
                      "standing_in": {
                        "2010": {
                          "post_id": "65808",
                          "name": "Dulwich and West Norwood",
                          "mapit_url": "http://mapit.mysociety.org/area/65808"
                        }
                      },
                      "homepage_url": "http://example.org/tessajowell",
                      "birth_date": "1947-09-17",
                      "wikipedia_url": "",
                      "party_memberships": {
                        "2010": {
                          "id": "party:53",
                          "name": "Labour Party"
                        }
                      },
                      "email": "tessa.jowell@example.com"
                    }
                  }
                ]
            ''',
        )
        factories.PartyFactory.reset_sequence()
        parties_extra = [
            factories.PartyExtraFactory.create()
            for i in range(4)
        ]
        for party_extra in parties_extra:
            gb_parties.parties.add(party_extra.base)
        labour_party_extra = parties_extra[0]
        green_party_extra = parties_extra[2]
        factories.CandidacyExtraFactory.create(
            election=election,
            base__person=person_extra.base,
            base__post=post_extra.base,
            base__on_behalf_of=labour_party_extra.base
        )
        factories.CandidacyExtraFactory.create(
            election=earlier_election,
            base__person=person_extra.base,
            base__post=post_extra.base,
            base__on_behalf_of=labour_party_extra.base
        )
        # Now create Shane Collins (who we'll merge into Tessa Jowell)
        person_extra = factories.PersonExtraFactory.create(
            base__id=2007,
            base__name='Shane Collins',
            base__gender='male',
            base__honorific_prefix='Mr',
            base__email='shane@gn.apc.org',
            versions='''
                [
                  {
                    "data": {
                      "birth_date": null,
                      "email": "shane@gn.apc.org",
                      "facebook_page_url": "",
                      "facebook_personal_url": "",
                      "gender": "male",
                      "homepage_url": "",
                      "honorific_prefix": "Mr",
                      "honorific_suffix": "",
                      "id": "2007",
                      "identifiers": [
                        {
                          "id": "547786cc737edc5252ce5af1",
                          "identifier": "2961",
                          "scheme": "yournextmp-candidate"
                        }
                      ],
                      "image": null,
                      "linkedin_url": "",
                      "name": "Shane Collins",
                      "other_names": [],
                      "party_memberships": {
                        "2010": {
                          "id": "party:63",
                          "name": "Green Party"
                        }
                      },
                      "party_ppc_page_url": "",
                      "proxy_image": null,
                      "standing_in": {
                        "2010": {
                          "mapit_url": "http://mapit.mysociety.org/area/65808",
                          "name": "Dulwich and West Norwood",
                          "post_id": "65808"
                        },
                        "2015": null
                      },
                      "twitter_username": "",
                      "wikipedia_url": ""
                    },
                    "information_source": "http://www.lambeth.gov.uk/sites/default/files/ec-dulwich-and-west-norwood-candidates-and-notice-of-poll-2015.pdf",
                    "timestamp": "2015-04-09T20:32:09.237610",
                    "username": "JPCarrington",
                    "version_id": "274e50504df330e4"
                  },
                  {
                    "data": {
                      "birth_date": null,
                      "email": "shane@gn.apc.org",
                      "facebook_page_url": null,
                      "facebook_personal_url": null,
                      "gender": "male",
                      "homepage_url": null,
                      "id": "2007",
                      "identifiers": [
                        {
                          "identifier": "2961",
                          "scheme": "yournextmp-candidate"
                        }
                      ],
                      "name": "Shane Collins",
                      "party_memberships": {
                        "2010": {
                          "id": "party:63",
                          "name": "Green Party"
                        }
                      },
                      "party_ppc_page_url": null,
                      "phone": "07939 196612",
                      "slug": "shane-collins",
                      "standing_in": {
                        "2010": {
                          "mapit_url": "http://mapit.mysociety.org/area/65808",
                          "name": "Dulwich and West Norwood",
                          "post_id": "65808"
                        }
                      },
                      "twitter_username": null,
                      "wikipedia_url": null
                    },
                    "information_source": "Imported from YourNextMP data from 2010",
                    "timestamp": "2014-11-21T18:16:47.670167",
                    "version_id": "68a452284d95d9ab"
                  }
                ]
            ''')
        factories.CandidacyExtraFactory.create(
            election=election,
            base__person=person_extra.base,
            base__post=post_extra.base,
            base__on_behalf_of=green_party_extra.base
        )
        factories.CandidacyExtraFactory.create(
            election=earlier_election,
            base__person=person_extra.base,
            base__post=post_extra.base,
            base__on_behalf_of=green_party_extra.base
        )

    def test_merge_disallowed_no_form(self):
        response = self.app.get('/person/2009/update', user=self.user)
        self.assertNotIn('person-merge', response.forms)

    def test_merge_two_people_disallowed(self):
        # Get the update page for the person just to get the CSRF token:
        response = self.app.get('/person/2009/update', user=self.user)
        csrftoken = self.app.cookies['csrftoken']
        response = self.app.post(
            '/person/2009/merge',
            {
                'csrfmiddlewaretoken': csrftoken,
                'other': '2007',
            },
            expect_errors=True
        )
        self.assertEqual(response.status_code, 403)

    @patch('candidates.views.version_data.get_current_timestamp')
    @patch('candidates.views.version_data.create_version_id')
    def test_merge_two_people(
            self,
            mock_create_version_id,
            mock_get_current_timestamp,
    ):
        mock_get_current_timestamp.return_value = example_timestamp
        mock_create_version_id.return_value = example_version_id

        response = self.app.get('/person/2009/update', user=self.user_who_can_merge)
        merge_form = response.forms['person-merge']
        merge_form['other'] = '2007'
        response = merge_form.submit()

        self.assertEqual(response.status_code, 302)
        self.assertEqual(
            response.location,
            'http://localhost:80/person/2009/tessa-jowell'
        )

        # Check that the redirect object has been made:
        self.assertEqual(
            PersonRedirect.objects.filter(
                old_person_id=2007,
                new_person_id=2009,
            ).count(),
            1
        )

        # Check that the other person was deleted (in the future we
        # might want to "soft delete" the person instead).
        self.assertEqual(Person.objects.filter(id=2007).count(), 0)

        # Get the merged person, and check that everything's as we expect:
        merged_person = Person.objects.get(id=2009)

        self.assertEqual(merged_person.birth_date, '')
        self.assertEqual(merged_person.email, 'jowell@example.com')
        self.assertEqual(merged_person.gender, 'female')
        self.assertEqual(merged_person.honorific_prefix, 'Mr')
        self.assertEqual(merged_person.honorific_suffix, 'DBE')

        candidacies = MembershipExtra.objects.filter(
            base__person=merged_person,
            base__role=F('election__candidate_membership_role')
        ).order_by('election__election_date')

        self.assertEqual(len(candidacies), 2)
        for c, expected_election in zip(candidacies, ('2010', '2015')):
            self.assertEqual(c.election.slug, expected_election)
            self.assertEqual(c.base.post.extra.slug, '65808')

        other_names = list(merged_person.other_names.all())
        self.assertEqual(len(other_names), 1)
        self.assertEqual(other_names[0].name, 'Shane Collins')
