from urlparse import urlsplit

from mock import patch

from django_webtest import WebTest

from .auth import TestUserMixin
from .helpers import equal_call_args
from .fake_popit import (
    FakeOrganizationCollection, FakePersonCollection, FakePostCollection,
    fake_mp_post_search_results
)
from ..models import LoggedAction

example_timestamp = '2014-09-29T10:11:59.216159'
example_version_id = '5aa6418325c1a0bb'

def fill_form(form, form_dict):
    for key, value in form_dict.items():
        form[key] = value

@patch('candidates.popit.PopIt')
class TestNewPersonView(TestUserMixin, WebTest):

    @patch('candidates.views.version_data.get_current_timestamp')
    @patch('candidates.views.version_data.create_version_id')
    @patch('candidates.models.popit.PopItPerson.create_new_person_in_popit')
    @patch('candidates.models.popit.PopItPerson.update_person_in_popit')
    def test_new_person_submission_refused_copyright(
            self,
            mock_update_person_in_popit,
            mock_create_new_person_in_popit,
            mock_create_version_id,
            mock_get_current_timestamp,
            mock_popit):
        # Get the constituency page:
        mock_popit.return_value.organizations = FakeOrganizationCollection
        mock_popit.return_value.persons = FakePersonCollection
        # Just a smoke test for the moment:
        response = self.app.get(
            '/constituency/65808/dulwich-and-west-norwood',
            user=self.user_refused
        )
        split_location = urlsplit(response.location)
        self.assertEqual(
            '/copyright-question',
            split_location.path
        )
        self.assertEqual(
            'next=/constituency/65808/dulwich-and-west-norwood',
            split_location.query
        )
        self.assertFalse(mock_create_new_person_in_popit.called)
        self.assertFalse(mock_update_person_in_popit.called)

    @patch('candidates.popit.requests')
    @patch('candidates.views.version_data.get_current_timestamp')
    @patch('candidates.views.version_data.create_version_id')
    @patch('candidates.models.popit.PopItPerson.update_person_in_popit')
    @patch.object(FakePersonCollection, 'post')
    def test_new_person_submission(
            self,
            mock_person_post,
            mock_update_person_in_popit,
            mock_create_version_id,
            mock_get_current_timestamp,
            mock_requests,
            mock_popit):
        # Get the constituency page:
        mock_popit.return_value.organizations = FakeOrganizationCollection
        mock_popit.return_value.persons = FakePersonCollection
        mock_popit.return_value.posts = FakePostCollection
        mock_requests.get.side_effect = fake_mp_post_search_results
        # Just a smoke test for the moment:
        response = self.app.get(
            '/election/2015/post/65808/dulwich-and-west-norwood',
            user=self.user
        )
        mock_get_current_timestamp.return_value = example_timestamp
        mock_create_version_id.return_value = example_version_id
        # Get the add candidate form and fill in some values:
        form = response.forms['new-candidate-form']
        form_dict = {
            'name': 'Jane Doe',
            # Make Jane Doe be standing for the Monster Raving Loony
            # Party in Dulwich and West Norwood:
            'party_gb_2015': 'party:66',
            'constituency_2015': '65808',
            'email': 'jane@example.com',
            'wikipedia_url': 'http://en.wikipedia.org/wiki/Jane_Doe',
        }
        fill_form(form, form_dict)
        mock_person_post.return_value = {
            'result': {
                'id': '1'
            }
        }
        submission_response = form.submit()

        # If there's no source specified, it shouldn't ever get to
        # update_person, and redirect back to the constituency page:
        self.assertFalse(mock_update_person_in_popit.called)

        # Try again with the source field filled in:
        form['source'] = 'A test new person, source: http://example.org'
        submission_response = form.submit()

        expected_call_args = ({
            "birth_date": None,
            "contact_details": [],
            "email": "jane@example.com",
            "gender": "",
            "honorific_prefix": "",
            "honorific_suffix": "",
            "id": "1",
            "links": [
               {
                    "note": "wikipedia",
                    "url": "http://en.wikipedia.org/wiki/Jane_Doe"
               }
            ],
            "name": "Jane Doe",
            "party_memberships": {
                "2015": {
                    "id": "party:66",
                    "name": "Official Monster Raving Loony Party"
            }
            },
            "standing_in": {
                "2015": {
                    "mapit_url": "http://mapit.mysociety.org/area/65808",
                    "name": "Dulwich and West Norwood",
                    "post_id": "65808"
                }
            },
            "versions": [
                {
                    "data": {
                        "birth_date": None,
                        "email": "jane@example.com",
                        "facebook_page_url": "",
                        "facebook_personal_url": "",
                        "gender": "",
                        "homepage_url": "",
                        "honorific_prefix": "",
                        "honorific_suffix": "",
                        "id": "1",
                        "identifiers": [],
                        "image": None,
                        "linkedin_url": "",
                        "name": "Jane Doe",
                        "other_names": [],
                        "party_memberships": {
                            "2015": {
                                "id": "party:66",
                                "name": "Official Monster Raving Loony Party"
                            }
                        },
                        "party_ppc_page_url": "",
                        "proxy_image": None,
                        "standing_in": {
                            "2015": {
                                "mapit_url": "http://mapit.mysociety.org/area/65808",
                                "name": "Dulwich and West Norwood",
                                "post_id": "65808"
                            }
                        },
                        "twitter_username": "",
                        "wikipedia_url": "http://en.wikipedia.org/wiki/Jane_Doe"
                    },
                    "information_source": "A test new person, source: http://example.org",
                    "timestamp": "2014-09-29T10:11:59.216159",
                    "username": "john",
                    "version_id": "5aa6418325c1a0bb"
                }
            ]
        },)

        self.assertEqual(mock_person_post.call_count, 1)
        self.assertTrue(
            equal_call_args(
                expected_call_args,
                mock_person_post.call_args_list[0][0]
            ),
            "create_person was called with unexpected values"
        )

        split_location = urlsplit(submission_response.location)
        self.assertEqual(
            '/person/1',
            split_location.path
        )

        # Find the most recent action in the actions table, and check
        # that it corresponds to this creation:
        last_logged_action = LoggedAction.objects.all().order_by('-created')[0]
        self.assertEqual(
            last_logged_action.popit_person_id,
            '1',
        )
        self.assertEqual(
            last_logged_action.popit_person_new_version,
            example_version_id,
        )
        self.assertEqual(
            last_logged_action.action_type,
            'person-create'
        )
