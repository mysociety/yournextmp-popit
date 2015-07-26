from copy import deepcopy
from mock import patch
from .helpers import equal_call_args

# from django.contrib.auth.models import User

from django_webtest import WebTest

from .auth import TestUserMixin
from .fake_popit import (
    FakePersonCollection, FakePostCollection, fake_mp_post_search_results
)

example_timestamp = '2014-09-29T10:11:59.216159'
example_version_id = '5aa6418325c1a0bb'


@patch('candidates.popit.requests')
@patch('candidates.popit.PopIt')
class TestRevertPersonView(TestUserMixin, WebTest):

    @patch.object(FakePersonCollection, 'put')
    @patch('candidates.views.version_data.get_current_timestamp')
    @patch('candidates.views.version_data.create_version_id')
    def test_revert_to_earlier_version(
            self,
            mock_create_version_id,
            mock_get_current_timestamp,
            mocked_put,
            mock_popit,
            mock_requests,
    ):
        mock_popit.return_value.persons = FakePersonCollection
        mock_popit.return_value.posts = FakePostCollection
        mock_get_current_timestamp.return_value = example_timestamp
        mock_create_version_id.return_value = example_version_id
        mock_requests.get.side_effect = fake_mp_post_search_results
               
        response = self.app.get('/person/2009/update', user=self.user)
        revert_form = response.forms['revert-form-5469de7db0cbd155']
        revert_form['source'] =  'Reverting to version 5469de7db0cbd155 for testing purposes'
        response = revert_form.submit()
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.location, 'http://localhost:80/person/2009')
        self.assertEqual(2, len(mocked_put.call_args_list))

        expected_purging_put = {
            u'contact_details': [],
            u'gender': '',
            u'honorific_prefix': '',
            u'honorific_suffix': '',
            u'identifiers': [
                {
                    u'id': u'544e3df981b7fa64bfccdaac',
                    u'identifier': u'2009',
                    u'scheme': u'yournextmp-candidate',
                },
                {
                    u'id': u'54d2d3725b6aac303dfcd68b',
                    u'identifier': u'uk.org.publicwhip/person/10326',
                    u'scheme': u'uk.org.publicwhip',
                }
            ],
            u'links': [],
            u'name': u'Tessa Jowell',
            u'url': u'http://candidates.127.0.0.1.xip.io:3000/api/v0.1/persons/2009',
            u'versions': [
                {
                    'data': {
                        'facebook_page_url': '',
                        'facebook_personal_url': '',
                        'name': u'Tessa Jowell',
                        'honorific_suffix': '',
                        'party_ppc_page_url': '',
                        'gender': '',
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
                        'linkedin_url': '',
                        'proxy_image': None,
                        'id': u'2009',
                        'other_names': [],
                        'honorific_prefix': '',
                        'standing_in': {
                            u'2010':
                            {
                                u'post_id': u'65808',
                                u'name': u'Dulwich and West Norwood',
                                u'mapit_url': u'http://mapit.mysociety.org/area/65808'
                            }
                        },
                        'homepage_url': '',
                        'twitter_username': '',
                        'wikipedia_url': '',
                        'party_memberships': {
                            u'2010': {
                                u'id': u'party:53',
                                u'name': u'Labour Party'
                            }
                        },
                        'birth_date': None,
                        'email': u'tessa.jowell@example.com'
                    },
                    'information_source': u'Reverting to version 5469de7db0cbd155 for testing purposes',
                    'timestamp': '2014-09-29T10:11:59.216159',
                    'username': u'john',
                    'version_id': '5aa6418325c1a0bb'
                },
                {
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
                    },
                    u'information_source': u'Just adding example data',
                    u'ip': u'127.0.0.1',
                    u'timestamp': u'2014-10-28T14:32:36.835429',
                    u'username': u'symroe',
                    u'version_id': u'35ec2d5821176ccc',
                },
                {
                    u'data': {
                        u'name': u'Tessa Jowell',
                        u'email': u'tessa.jowell@example.com',
                        u'twitter_username': u'',
                        u'standing_in': {
                            u'2010': {
                                u'post_id': u'65808',
                                u'name': u'Dulwich and West Norwood',
                                u'mapit_url': u'http://mapit.mysociety.org/area/65808'
                            }
                        },
                        u'homepage_url': u'',
                        u'wikipedia_url': u'',
                        u'party_memberships': {
                            u'2010': {
                                u'id': u'party:53',
                                u'name': u'Labour Party'
                            }
                        },
                        u'birth_date': None,
                        u'id': u'2009'
                    },
                    u'username': u'mark',
                    u'information_source': u'An initial version',
                    u'ip': u'127.0.0.1',
                    u'timestamp': u'2014-10-01T15:12:34.732426',
                    u'version_id': u'5469de7db0cbd155',
                }
            ],
            u'other_names': [],
            u'html_url': u'http://candidates.127.0.0.1.xip.io:3000/persons/2009',
            u'slug': u'tessa-jowell',
            u'phone': u'02086931826',
            u'email': u'tessa.jowell@example.com',
            u'standing_in': None,
            u'party_memberships': None,
            'birth_date': None,
            u'id': u'2009'
        }

        self.assertTrue(
            equal_call_args(
                (expected_purging_put,),
                mocked_put.call_args_list[0][0]
            )
        )

        expected_real_put = deepcopy(expected_purging_put)
        expected_real_put['party_memberships'] = {
            "2010": {
                "id": "party:53", 
                "name": "Labour Party"
            }
        }
        expected_real_put['standing_in'] = {
            "2010": {
                "mapit_url": "http://mapit.mysociety.org/area/65808", 
                "name": "Dulwich and West Norwood", 
                "post_id": "65808"
            }
        }


        self.assertTrue(
            equal_call_args(
                (expected_real_put,),
                mocked_put.call_args_list[1][0]
            )
        )
