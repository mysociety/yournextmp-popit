from copy import deepcopy
from mock import patch
from .helpers import equal_call_args

# from django.contrib.auth.models import User

from django_webtest import WebTest

from candidates.models import PersonRedirect
from .auth import TestUserMixin
from .fake_popit import FakePersonCollection, fake_mp_post_search_results

example_timestamp = '2014-09-29T10:11:59.216159'
example_version_id = '5aa6418325c1a0bb'


@patch('candidates.popit.PopIt')
@patch('candidates.popit.requests')
class TestMergePeopleView(TestUserMixin, WebTest):

    def test_merge_disallowed_no_form(self, mock_requests, mock_popit):
        mock_popit.return_value.persons = FakePersonCollection
        mock_requests.get.side_effect = fake_mp_post_search_results
        response = self.app.get('/person/2009/update', user=self.user)
        self.assertNotIn('person-merge', response.forms)

    @patch.object(FakePersonCollection, 'put')
    def test_merge_two_people_disallowed(
            self,
            mocked_put,
            mock_requests,
            mock_popit,
    ):
        mock_popit.return_value.persons = FakePersonCollection
        mock_requests.get.side_effect = fake_mp_post_search_results
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
        self.assertFalse(mocked_put.called)
        self.assertEqual(response.status_code, 403)


    @patch.object(FakePersonCollection, 'put')
    @patch.object(FakePersonCollection, 'delete')
    @patch('candidates.views.version_data.get_current_timestamp')
    @patch('candidates.views.version_data.create_version_id')
    def test_merge_two_people(
            self,
            mock_create_version_id,
            mock_get_current_timestamp,
            mocked_delete,
            mocked_put,
            mock_requests,
            mock_popit
    ):
        mock_popit.return_value.persons = FakePersonCollection
        mock_requests.get.side_effect = fake_mp_post_search_results
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

        mocked_delete.assert_called_once_with()
        self.assertEqual(
            PersonRedirect.objects.filter(
                old_person_id=2007,
                new_person_id=2009,
            ).count(),
            1
        )

        self.assertEqual(2, len(mocked_put.call_args_list))

        expected_purging_put = {
            "birth_date": None,
            "contact_details": [],
            "email": "jowell@example.com",
            "gender": "female",
            "honorific_prefix": "Ms",
            "honorific_suffix": "DBE",
            "html_url": "http://candidates.127.0.0.1.xip.io:3000/persons/2009",
            "id": "2009",
            "identifiers": [
                {
                    "id": "544e3df981b7fa64bfccdaac",
                    "scheme": "yournextmp-candidate",
                    "identifier": "2009"
                },
                {
                    "id": "54d2d3725b6aac303dfcd68b",
                    "scheme": "uk.org.publicwhip",
                    "identifier": "uk.org.publicwhip/person/10326"
                },
                {
                    "id": "552f855ced1c6ee164eecba5",
                    "identifier": "2961",
                    "scheme": "yournextmp-candidate"
                }
            ],
            "links": [],
            "name": "Tessa Jowell",
            "phone": "02086931826",
            "other_names": [],
            "party_memberships": None,
            "slug": "tessa-jowell",
            "standing_in": None,
            "url": "http://candidates.127.0.0.1.xip.io:3000/api/v0.1/persons/2009",
            "versions": [
                {
                    "data": {
                        "birth_date": None,
                        "email": "jowell@example.com",
                        "facebook_page_url": "",
                        "facebook_personal_url": "",
                        "gender": "female",
                        "homepage_url": "",
                        "honorific_prefix": "Ms",
                        "honorific_suffix": "DBE",
                        "id": "2009",
                        "identifiers": [
                            {
                                "id": "544e3df981b7fa64bfccdaac",
                                "identifier": "2009",
                                "scheme": "yournextmp-candidate"
                            },
                            {
                                "id": "54d2d3725b6aac303dfcd68b",
                                "identifier": "uk.org.publicwhip/person/10326",
                                "scheme": "uk.org.publicwhip"
                            },
                            {
                                "id": "552f855ced1c6ee164eecba5",
                                "identifier": "2961",
                                "scheme": "yournextmp-candidate"
                            }
                        ],
                        "image": None,
                        "linkedin_url": "",
                        "name": "Tessa Jowell",
                        "other_names": [
                            {
                                "name": "Shane Collins"
                            }
                        ],
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
                                "post_id": "65808"
                            },
                            "2015": {
                                "mapit_url": "http://mapit.mysociety.org/area/65808",
                                "name": "Dulwich and West Norwood",
                                "post_id": "65808"
                            }
                        },
                        "twitter_username": "",
                        "wikipedia_url": ""
                    },
                    "information_source": "After merging person 2007",
                    "timestamp": "2014-09-29T10:11:59.216159",
                    "username": "alice",
                    "version_id": "5aa6418325c1a0bb"
                },
                {
                    "username": "symroe",
                    "information_source": "Just adding example data",
                    "ip": "127.0.0.1",
                    "version_id": "35ec2d5821176ccc",
                    "timestamp": "2014-10-28T14:32:36.835429",
                    "data": {
                        "name": "Tessa Jowell",
                        "id": "2009",
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
                        "homepage_url": "",
                        "birth_date": None,
                        "wikipedia_url": "",
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
                        "homepage_url": "",
                        "birth_date": None,
                        "wikipedia_url": "",
                        "party_memberships": {
                            "2010": {
                                "id": "party:53",
                                "name": "Labour Party"
                            }
                        },
                        "email": "tessa.jowell@example.com"
                    }
                },
                {
                    "data": {
                        "birth_date": None,
                        "email": "shane@gn.apc.org",
                        "facebook_page_url": "",
                        "facebook_personal_url": "",
                        "gender": "male",
                        "homepage_url": "",
                        "honorific_prefix": "",
                        "honorific_suffix": "",
                        "id": "2007",
                        "identifiers": [
                            {
                                "id": "547786cc737edc5252ce5af1",
                                "identifier": "2961",
                                "scheme": "yournextmp-candidate"
                            }
                        ],
                        "image": None,
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
                        "proxy_image": None,
                        "standing_in": {
                            "2010": {
                                "mapit_url": "http://mapit.mysociety.org/area/65808",
                                "name": "Dulwich and West Norwood",
                                "post_id": "65808"
                            },
                            "2015": None
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
                        "birth_date": None,
                        "email": "shane@gn.apc.org",
                        "facebook_page_url": None,
                        "facebook_personal_url": None,
                        "gender": "male",
                        "homepage_url": None,
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
                        "party_ppc_page_url": None,
                        "phone": "07939 196612",
                        "slug": "shane-collins",
                        "standing_in": {
                            "2010": {
                                "mapit_url": "http://mapit.mysociety.org/area/65808",
                                "name": "Dulwich and West Norwood",
                                "post_id": "65808"
                            }
                        },
                        "twitter_username": None,
                        "wikipedia_url": None
                    },
                    "information_source": "Imported from YourNextMP data from 2010",
                    "timestamp": "2014-11-21T18:16:47.670167",
                    "version_id": "68a452284d95d9ab"
                }
            ]
        }

        self.assertTrue(
            equal_call_args(
                (expected_purging_put,),
                mocked_put.call_args_list[0][0]
            )
        )

        expected_real_put = deepcopy(expected_purging_put)

        expected_real_put['standing_in'] = {
            "2010": {
                "mapit_url": "http://mapit.mysociety.org/area/65808",
                "name": "Dulwich and West Norwood",
                "post_id": "65808"
            },
            "2015": {
                "mapit_url": "http://mapit.mysociety.org/area/65808",
                "name": "Dulwich and West Norwood",
                "post_id": "65808"
            }
        }
        expected_real_put['party_memberships'] = {
            "2010": {
                "id": "party:53",
                "name": "Labour Party"
            },
            "2015": {
                "id": "party:53",
                "name": "Labour Party"
            }
        }
        expected_real_put['other_names'] = [
            {
                "name": "Shane Collins"
            }
        ]

        self.assertTrue(
            equal_call_args(
                (expected_real_put,),
                mocked_put.call_args_list[1][0]
            )
        )
