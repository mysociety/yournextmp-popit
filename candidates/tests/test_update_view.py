from urlparse import urlsplit

from mock import patch

from django_webtest import WebTest

from .auth import TestUserMixin
from .helpers import equal_call_args
from .fake_popit import (
    FakePersonCollection, FakePostCollection, fake_mp_post_search_results
)

example_timestamp = '2014-09-29T10:11:59.216159'
example_version_id = '5aa6418325c1a0bb'

@patch('candidates.popit.PopIt')
@patch.object(FakePersonCollection, 'put')
class TestUpdatePersonView(TestUserMixin, WebTest):

    def test_update_person_view_get_without_login(self, mocked_person_put, mock_popit):
        response = self.app.get('/person/2009/update')
        self.assertEqual(response.status_code, 302)
        split_location = urlsplit(response.location)
        self.assertEqual('/accounts/login/', split_location.path)
        self.assertEqual('next=/person/2009/update', split_location.query)
        self.assertFalse(mocked_person_put.called)

    def test_update_person_view_get_refused_copyright(self, mocked_person_put, mock_popit):
        response = self.app.get('/person/2009/update', user=self.user_refused)
        self.assertEqual(response.status_code, 302)
        split_location = urlsplit(response.location)
        self.assertEqual('/copyright-question', split_location.path)
        self.assertEqual('next=/person/2009/update', split_location.query)
        self.assertFalse(mocked_person_put.called)


    @patch('candidates.popit.requests')
    def test_update_person_view_get(self, mock_requests, mocked_person_put, mock_popit):
        mock_popit.return_value.persons = FakePersonCollection
        mock_requests.get.side_effect = fake_mp_post_search_results
        # For the moment just check that the form's actually there:
        response = self.app.get('/person/2009/update', user=self.user)
        response.forms['person-details']
        self.assertFalse(mocked_person_put.called)

    @patch('candidates.popit.requests')
    @patch('candidates.views.version_data.get_current_timestamp')
    @patch('candidates.views.version_data.create_version_id')
    def test_update_person_submission_copyright_refused(
            self,
            mock_create_version_id,
            mock_get_current_timestamp,
            mock_requests,
            mocked_person_put,
            mock_popit):
        mock_popit.return_value.persons = FakePersonCollection
        mock_get_current_timestamp.return_value = example_timestamp
        mock_create_version_id.return_value = example_version_id
        mock_requests.get.side_effect = fake_mp_post_search_results
        response = self.app.get('/person/2009/update', user=self.user)
        form = response.forms['person-details']
        form['wikipedia_url'] = 'http://en.wikipedia.org/wiki/Tessa_Jowell'
        form['party_gb_2015'] = 'party:90'
        form['party_ni_2015'] = 'party:none'
        form['source'] = "Some source of this information"
        submission_response = form.submit(user=self.user_refused)
        split_location = urlsplit(submission_response.location)
        self.assertEqual('/copyright-question', split_location.path)
        self.assertEqual('next=/person/2009/update', split_location.query)
        self.assertFalse(mocked_person_put.called)

    @patch('candidates.popit.requests')
    @patch('candidates.views.version_data.get_current_timestamp')
    @patch('candidates.views.version_data.create_version_id')
    def test_update_person_submission(
            self,
            mock_create_version_id,
            mock_get_current_timestamp,
            mock_requests,
            mocked_person_put,
            mock_popit):
        mock_popit.return_value.persons = FakePersonCollection
        mock_popit.return_value.posts = FakePostCollection
        mock_get_current_timestamp.return_value = example_timestamp
        mock_create_version_id.return_value = example_version_id
        mock_requests.get.side_effect = fake_mp_post_search_results
        response = self.app.get(
            '/person/2009/update',
            user=self.user_who_can_lock,
        )
        form = response.forms['person-details']
        form['wikipedia_url'] = 'http://en.wikipedia.org/wiki/Tessa_Jowell'
        form['party_gb_2015'] = 'party:90'
        form['party_ni_2015'] = 'party:none'
        form['source'] = "Some source of this information"
        submission_response = form.submit()

        expected_purging_put = {
            u'slug': u'tessa-jowell',
            u'contact_details': [],
            u'name': u'Tessa Jowell',
            u'links': [],
            u'honorific_suffix': u'DBE',
            u'url': u'http://candidates.127.0.0.1.xip.io:3000/api/v0.1/persons/2009',
            u'gender':
            u'female',
            u'identifiers': [
                {
                    u'scheme': u'yournextmp-candidate',
                    u'id': u'544e3df981b7fa64bfccdaac',
                    u'identifier': u'2009'
                },
                {
                    u'scheme': u'uk.org.publicwhip',
                    u'id': u'54d2d3725b6aac303dfcd68b',
                    u'identifier': u'uk.org.publicwhip/person/10326'
                }
            ],
            u'other_names': [],
            u'html_url': u'http://candidates.127.0.0.1.xip.io:3000/persons/2009',
            u'standing_in': None,
            u'honorific_prefix': u'Ms',
            u'phone': u'02086931826',
            u'versions': [
                {
                    'information_source': u'Some source of this information',
                    'timestamp': '2014-09-29T10:11:59.216159',
                    'username': u'charles',
                    'data': {
                        'facebook_page_url': u'',
                        'facebook_personal_url': u'',
                        'name': u'Tessa Jowell',
                        'honorific_suffix': u'DBE',
                        'party_ppc_page_url': u'',
                        'gender': u'female',
                        'image': None,
                        'identifiers': [
                            {
                                u'scheme': u'yournextmp-candidate',
                                u'id': u'544e3df981b7fa64bfccdaac',
                                u'identifier': u'2009'
                            },
                            {
                                u'scheme': u'uk.org.publicwhip',
                                u'id': u'54d2d3725b6aac303dfcd68b',
                                u'identifier': u'uk.org.publicwhip/person/10326'
                            }
                        ],
                        'linkedin_url': u'',
                        'proxy_image': None,
                        'id': u'2009',
                        'other_names': [],
                        'honorific_prefix': u'Ms',
                        'standing_in': {
                            u'2015': {
                                'post_id': u'65808',
                                'name': u'Dulwich and West Norwood',
                                'mapit_url': 'http://mapit.mysociety.org/area/65808'
                            },
                            u'2010': {
                                u'post_id': u'65808',
                                u'name': u'Dulwich and West Norwood',
                                u'mapit_url': u'http://mapit.mysociety.org/area/65808'
                            }
                        },
                        'homepage_url': u'',
                        'twitter_username': u'',
                        'wikipedia_url': u'http://en.wikipedia.org/wiki/Tessa_Jowell',
                        'party_memberships': {
                            u'2015': {
                                'name': u'Liberal Democrats',
                                'id': u'party:90'
                            },
                            u'2010': {
                                u'id': u'party:53',
                                u'name': u'Labour Party'
                            }
                        },
                        'birth_date': None,
                        'email': u'jowell@example.com'
                    },
                    'version_id': '5aa6418325c1a0bb'
                },
                {
                    u'username': u'symroe',
                    u'information_source': u'Just adding example data',
                    u'timestamp': u'2014-10-28T14:32:36.835429',
                    u'version_id': u'35ec2d5821176ccc',
                    u'ip': u'127.0.0.1',
                    u'data': {
                        u'name': u'Tessa Jowell',
                        u'email': u'jowell@example.com',
                        u'twitter_username': u'',
                        u'standing_in': {
                            u'2015': {
                                u'post_id': u'65808',
                                u'name': u'Dulwich and West Norwood',
                                u'mapit_url': u'http://mapit.mysociety.org/area/65808'
                            },
                            u'2010': {
                                u'post_id': u'65808',
                                u'name': u'Dulwich and West Norwood',
                                u'mapit_url': u'http://mapit.mysociety.org/area/65808'
                            }
                        },
                        u'homepage_url': u'',
                        u'wikipedia_url': u'',
                        u'party_memberships': {
                            u'2015': {
                                u'id': u'party:53',
                                u'name': u'Labour Party'
                            },
                            u'2010': {
                                u'id': u'party:53',
                                u'name': u'Labour Party'
                            }
                        },
                        u'birth_date': None,
                        u'id': u'2009'
                    }
                },
                {
                    "data": {
                        "birth_date": None,
                        "email": "tessa.jowell@example.com",
                        "homepage_url": "",
                        "id": "2009",
                        "name": "Tessa Jowell",
                        "party_memberships": {
                            "2010": {
                                "id": "party:53",
                                "name": "Labour Party"
                            }
                        },
                        "standing_in": {
                            "2010": {
                                "mapit_url": "http://mapit.mysociety.org/area/65808",
                                "name": "Dulwich and West Norwood",
                                "post_id": "65808"
                            }
                        },
                        "twitter_username": "",
                        "wikipedia_url": ""
                    },
                    "information_source": "An initial version",
                    "ip": "127.0.0.1",
                    "timestamp": "2014-10-01T15:12:34.732426",
                    "username": "mark",
                    "version_id": "5469de7db0cbd155"
                }
            ],
            'birth_date': None,
            u'party_memberships': None,
            u'id': u'2009',
            u'email': u'jowell@example.com'
        }

        self.assertTrue(
            equal_call_args(
                (expected_purging_put,),
                mocked_person_put.call_args_list[0][0]
            ),
            "the purging PUT was called with unexpected values"
        )

        expected_actual_put = {
            u'slug': u'tessa-jowell',
            u'contact_details': [],
            u'name': u'Tessa Jowell',
            u'links': [
                {
                    'note': 'wikipedia',
                    'url': u'http://en.wikipedia.org/wiki/Tessa_Jowell'
                }
            ],
            u'honorific_suffix': u'DBE',
            u'url': u'http://candidates.127.0.0.1.xip.io:3000/api/v0.1/persons/2009',
            u'gender': u'female',
            u'identifiers': [
                {
                    u'scheme': u'yournextmp-candidate',
                    u'id': u'544e3df981b7fa64bfccdaac',
                    u'identifier': u'2009'
                },
                {
                    u'scheme': u'uk.org.publicwhip',
                    u'id': u'54d2d3725b6aac303dfcd68b',
                    u'identifier': u'uk.org.publicwhip/person/10326'
                }
            ],
            u'other_names': [],
            u'html_url': u'http://candidates.127.0.0.1.xip.io:3000/persons/2009',
            u'standing_in': {
                u'2015': {
                    'post_id': u'65808',
                    'name': u'Dulwich and West Norwood',
                    'mapit_url': 'http://mapit.mysociety.org/area/65808'
                },
                u'2010': {
                    u'post_id': u'65808',
                    u'name': u'Dulwich and West Norwood',
                    u'mapit_url': u'http://mapit.mysociety.org/area/65808'
                }
            },
            u'honorific_prefix': u'Ms',
            u'phone': u'02086931826',
            u'versions': [
                {
                    'information_source': u'Some source of this information',
                    'timestamp': '2014-09-29T10:11:59.216159',
                    'username': u'charles',
                    'data': {
                        'facebook_page_url': u'',
                        'facebook_personal_url': u'',
                        'name': u'Tessa Jowell',
                        'honorific_suffix': u'DBE',
                        'party_ppc_page_url': u'',
                        'gender': u'female',
                        'image': None,
                        'identifiers': [
                            {
                                u'scheme': u'yournextmp-candidate',
                                u'id': u'544e3df981b7fa64bfccdaac',
                                u'identifier': u'2009'
                            },
                            {
                                u'scheme': u'uk.org.publicwhip',
                                u'id': u'54d2d3725b6aac303dfcd68b',
                                u'identifier': u'uk.org.publicwhip/person/10326'
                            }
                        ],
                        'linkedin_url': u'',
                        'proxy_image': None,
                        'id': u'2009',
                        'other_names': [],
                        'honorific_prefix': u'Ms',
                        'standing_in': {
                            u'2015': {
                                'post_id': u'65808',
                                'name': u'Dulwich and West Norwood',
                                'mapit_url': 'http://mapit.mysociety.org/area/65808'
                            },
                            u'2010': {
                                u'post_id': u'65808',
                                u'name': u'Dulwich and West Norwood',
                                u'mapit_url': u'http://mapit.mysociety.org/area/65808'
                            }
                        },
                        'homepage_url': u'',
                        'twitter_username': u'',
                        'wikipedia_url': u'http://en.wikipedia.org/wiki/Tessa_Jowell',
                        'party_memberships': {
                            u'2015': {
                                'name': u'Liberal Democrats',
                                'id': u'party:90'
                            },
                            u'2010': {
                                u'id': u'party:53',
                                u'name': u'Labour Party'
                            }
                        },
                        'birth_date': None,
                        'email': u'jowell@example.com'
                    },
                    'version_id': '5aa6418325c1a0bb'
                },
                {
                    u'username': u'symroe',
                    u'information_source': u'Just adding example data',
                    u'timestamp': u'2014-10-28T14:32:36.835429',
                    u'version_id': u'35ec2d5821176ccc',
                    u'ip': u'127.0.0.1',
                    u'data': {
                        u'name': u'Tessa Jowell',
                        u'email': u'jowell@example.com',
                        u'twitter_username': u'',
                        u'standing_in': {
                            u'2015': {
                                u'post_id': u'65808',
                                u'name': u'Dulwich and West Norwood',
                                u'mapit_url': u'http://mapit.mysociety.org/area/65808'
                            },
                            u'2010': {
                                u'post_id': u'65808',
                                u'name': u'Dulwich and West Norwood',
                                u'mapit_url': u'http://mapit.mysociety.org/area/65808'
                            }
                        },
                        u'homepage_url': u'',
                        u'wikipedia_url': u'',
                        u'party_memberships': {
                            u'2015': {
                                u'id': u'party:53',
                                u'name': u'Labour Party'
                            },
                            u'2010': {
                                u'id': u'party:53',
                                u'name': u'Labour Party'
                            }
                        },
                        u'birth_date': None,
                        u'id': u'2009'
                    }
                },
                {
                    "data": {
                        "birth_date": None,
                        "email": "tessa.jowell@example.com",
                        "homepage_url": "",
                        "id": "2009",
                        "name": "Tessa Jowell",
                        "party_memberships": {
                            "2010": {
                                "id": "party:53",
                                "name": "Labour Party"
                            }
                        },
                        "standing_in": {
                            "2010": {
                                "mapit_url": "http://mapit.mysociety.org/area/65808",
                                "name": "Dulwich and West Norwood",
                                "post_id": "65808"
                            }
                        },
                        "twitter_username": "",
                        "wikipedia_url": ""
                    },
                    "information_source": "An initial version",
                    "ip": "127.0.0.1",
                    "timestamp": "2014-10-01T15:12:34.732426",
                    "username": "mark",
                    "version_id": "5469de7db0cbd155"
                }
            ],
            'birth_date': None,
            u'party_memberships': {
                u'2015': {
                    'name': u'Liberal Democrats',
                    'id': u'party:90'
                },
                u'2010': {
                    u'id': u'party:53',
                    u'name': u'Labour Party'
                }
            },
            u'id': u'2009',
            u'email': u'jowell@example.com'
        }

        self.assertTrue(
            equal_call_args(
                (expected_actual_put,),
                mocked_person_put.call_args_list[1][0]
            ),
            "the actual PUT was called with unexpected values"
        )

        # It should redirect back to the same person's page:
        split_location = urlsplit(submission_response.location)
        self.assertEqual(
            '/person/2009',
            split_location.path
        )
