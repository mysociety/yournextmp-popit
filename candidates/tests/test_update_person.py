from copy import deepcopy

from django.test import TestCase

from mock import patch, MagicMock

from candidates.models import PopItPerson

from .fake_popit import FakePersonCollection

from .helpers import equal_call_args


class TestUpdatePerson(TestCase):

    @patch.object(FakePersonCollection, 'put')
    @patch('candidates.models.popit.invalidate_posts')
    @patch('candidates.models.popit.invalidate_person')
    def test_update_tessa_jowell(
            self,
            mock_invalidate_person,
            mock_invalidate_posts,
            mocked_put
    ):

        mock_api = MagicMock()
        mock_api.persons = FakePersonCollection

        old_person_data = {
            "birth_date": '1947',
            "email": "foo@example.org",
            "facebook_page_url": "",
            "facebook_personal_url": "",
            "gender": "",
            "homepage_url": "http://foo.example.org",
            "honorific_prefix": "",
            "honorific_suffix": "",
            "id": "2009",
            "identifiers": [],
            "image": None,
            "linkedin_url": "",
            "name": "Tessa Jowell",
            "other_names": [],
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
            "party_ppc_page_url": "",
            "proxy_image": None,
            "standing_in": {
                "2010": {
                    "mapit_url": "http://mapit.mysociety.org/area/65808",
                    "name": "Dulwich and West Norwood",
                    "post_id": "65808",
                },
                "2015": {
                    "mapit_url": "http://mapit.mysociety.org/area/65913",
                    "name": "Camberwell and Peckham",
                    "post_id": "65913",
                }
            },
            "twitter_username": "jowellt",
            "wikipedia_url": "",
        }

        new_person_data = deepcopy(old_person_data)
        new_person_data['standing_in']['2015'] = {
            "mapit_url": "http://mapit.mysociety.org/area/65808",
            "name": "Dulwich and West Norwood",
            "post_id": "65808",
        }

        previous_version = {
            'data': {
                "name": "Tessa Jowell",
                "standing_in": {
                    "2010": {
                        "mapit_url": "http://mapit.mysociety.org/area/65808",
                        "name": "Dulwich and West Norwood",
                        "post_id": "65808",
                    },
                    "2015": {
                        "mapit_url": "http://mapit.mysociety.org/area/65913",
                        "name": "Camberwell and Peckham",
                        "post_id": "65913",
                    }
                },
            }
        }

        person = PopItPerson.create_from_reduced_json(old_person_data)
        person.update_from_reduced_json(new_person_data)
        person.versions = [previous_version]
        person.record_version(
            {
                'information_source': 'A change made for testing purposes',
                'username': 'tester',
                'version_id': '6054aa38b30b4418',
                'timestamp': '2014-09-28T14:02:44.567413',
            },
        )
        person.save_to_popit(mock_api)

        self.assertEqual(2, len(mocked_put.call_args_list))

        first_put_call_args = {
                'birth_date': '1947',
                'contact_details': [],
                'email': u'foo@example.org',
                'gender': '',
                'honorific_prefix': '',
                'honorific_suffix': '',
                'id': '2009',
                'identifiers': [],
                'name': u'Tessa Jowell',
                'links': [],
                'other_names': [],
                'party_memberships': None,
                'standing_in': None,
                'versions': [
                    {
                        'username': 'tester',
                        'information_source': 'A change made for testing purposes',
                        'version_id': '6054aa38b30b4418',
                        'timestamp': '2014-09-28T14:02:44.567413',
                        'data': new_person_data
                    },
                    previous_version
                ],
            }

        second_put_call_args = {
                'birth_date': '1947',
                'contact_details': [
                    {
                        'type': 'twitter',
                        'value': 'jowellt'
                    }
                ],
                'email': u'foo@example.org',
                'gender': '',
                'honorific_prefix': '',
                'honorific_suffix': '',
                'id': '2009',
                'identifiers': [],
                'name': u'Tessa Jowell',
                'links': [
                    {
                        'note': 'homepage',
                        'url': 'http://foo.example.org'
                    }
                ],
                'other_names': [],
                'party_memberships': {
                    '2010': {
                        'id': 'party:53',
                        'name': 'Labour Party'
                    },
                    '2015': {
                        'id': 'party:53',
                        'name': 'Labour Party'
                    }
                },
                'standing_in': {
                    '2015': {
                        'name': 'Dulwich and West Norwood',
                        'mapit_url': 'http://mapit.mysociety.org/area/65808',
                        'post_id': '65808',
                    },
                    '2010': {
                        'name': 'Dulwich and West Norwood',
                        'mapit_url': 'http://mapit.mysociety.org/area/65808',
                        'post_id': '65808',
                    }
                },
                'versions': [
                    {
                        'username': 'tester',
                        'information_source': 'A change made for testing purposes',
                        'version_id': '6054aa38b30b4418',
                        'timestamp': '2014-09-28T14:02:44.567413',
                        'data': new_person_data
                    },
                    previous_version
                ],
            }


        self.assertTrue(
            equal_call_args(
                [first_put_call_args],
                mocked_put.call_args_list[0][0],
            ),
            "Unexpected first PUT (the one blanking out standing_in and party_memberships",
        )

        self.assertTrue(
            equal_call_args(
                [second_put_call_args],
                mocked_put.call_args_list[1][0],
            ),
            "Unexpected second PUT (the one with real standing_in and party_memberships",
        )

        self.assertEqual(4, mock_api.memberships.post.call_count)

        posted_memberships = [
            c[0][0]
            for c in mock_api.memberships.post.call_args_list
        ]

        self.assertEqual(
            posted_memberships,
            [
                {
                    "end_date": "9999-12-31",
                    "person_id": "2009",
                    "post_id": "65808",
                    "role": "Candidate",
                    "start_date": "2010-05-07"
                },
                {
                    "end_date": "2010-05-06",
                    "person_id": "2009",
                    "post_id": "65808",
                    "role": "Candidate",
                    "start_date": "2005-05-06"
                },
                {
                    "end_date": "9999-12-31",
                    "organization_id": "party:53",
                    "person_id": "2009",
                    "start_date": "2010-05-07"
                },
                {
                    "end_date": "2010-05-06",
                    "organization_id": "party:53",
                    "person_id": "2009",
                    "start_date": "2005-05-06"
                },
            ]
        )

        mock_invalidate_person.assert_called_with('2009')

        mock_invalidate_posts.assert_called_with(set(['65808', '65913']))
