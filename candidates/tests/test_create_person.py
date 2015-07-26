from django.contrib.auth.models import AnonymousUser
from django_webtest import WebTest

from mock import patch, MagicMock

from .auth import TestUserMixin
from .fake_popit import FakePersonCollection, FakePostCollection
from .helpers import equal_call_args
from ..popit import PopItApiMixin
from ..models import PopItPerson

class MinimalUpdateClass(PopItApiMixin):

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super(MinimalUpdateClass, self).__init__(*args, **kwargs)
        self.request = MagicMock()
        if user is None:
            self.request.user = AnonymousUser()
        else:
            self.request.user = user


EXPECTED_ARGS = {
    'birth_date': '1988-01-01',
    'email': u'jane@example.org',
    'gender': 'female',
    'honorific_prefix': '',
    'honorific_suffix': '',
    'id': '1',
    'identifiers': [
        {
            'scheme': 'yournextmp-candidate',
            'identifier': '1234567'
        }
    ],
    'links': [
        {
            'note': 'facebook page',
            'url': 'http://notreallyfacebook/tessajowellcampaign',
        },
        {
            'note': 'party candidate page',
            'url': 'http://labour.example.org/tessajowell',
        },
        {
            'note': 'facebook personal',
            'url': 'http://notreallyfacebook/tessajowell',
        },
        {
            'note': 'homepage',
            'url': 'http://janedoe.example.org'
        },
    ],
    'name': u'Jane Doe',
    'party_memberships': {
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
        }
    },
    'versions': [
        {
            'information_source': 'A change made for testing purposes',
            'username': 'tester',
            'version_id': '6054aa38b30b4418',
            'timestamp': '2014-09-28T14:02:44.567413',
            'data': {
                'twitter_username': '',
                'standing_in': {
                    '2015': {
                        'name': 'Dulwich and West Norwood',
                        'mapit_url': 'http://mapit.mysociety.org/area/65808',
                        'post_id': '65808',
                    }
                },
                'homepage_url': 'http://janedoe.example.org',
                'identifiers': [
                    {
                        'scheme': 'yournextmp-candidate',
                        'identifier': '1234567'
                    }
                ],
                'facebook_page_url': 'http://notreallyfacebook/tessajowellcampaign',
                'facebook_personal_url': 'http://notreallyfacebook/tessajowell',
                'party_ppc_page_url': 'http://labour.example.org/tessajowell',
                'birth_date': '1988-01-01',
                'gender': 'female',
                'honorific_prefix': '',
                'honorific_suffix': '',
                'image': None,
                'linkedin_url': '',
                'name': 'Jane Doe',
                'other_names': [],
                'proxy_image': None,
                'wikipedia_url': '',
                'party_memberships': {
                    '2015': {
                        'id': 'party:53',
                        'name': 'Labour Party'
                    }
                },
                'email': 'jane@example.org',
                'id': '1'
            }
        }
    ],
}

NEW_PERSON_DATA = {
    "birth_date": None,
    "email": "jane@example.org",
    "gender": "female",
    "homepage_url": "http://janedoe.example.org",
    "identifiers": [
        {
            "scheme": "yournextmp-candidate",
            "identifier": "1234567"
        }
    ],
    "name": "Jane Doe",
    "party_memberships": {
        "2015": {
            "id": "party:53",
            "name": "Labour Party"
        }
    },
    "standing_in": {
        "2015": {
            "mapit_url": "http://mapit.mysociety.org/area/65808",
            "post_id": "65808",
            "name": "Dulwich and West Norwood"
        }
    },
    "twitter_username": "",
    "wikipedia_url": "",
    "facebook_personal_url": "http://notreallyfacebook/tessajowell",
    "facebook_page_url": "http://notreallyfacebook/tessajowellcampaign",
    "party_ppc_page_url": "http://labour.example.org/tessajowell",
    "birth_date": "1988-01-01",
}

@patch.object(FakePersonCollection, 'post')
def mock_create_person(mocked_post):
    mocked_post.return_value = {
        'result': {
            'id': '1'
        }
    }

    mock_api = MagicMock()
    mock_api.persons = FakePersonCollection

    person = PopItPerson.create_from_reduced_json(NEW_PERSON_DATA)
    person.record_version(
        {
            'information_source': 'A change made for testing purposes',
            'username': 'tester',
            'version_id': '6054aa38b30b4418',
            'timestamp': '2014-09-28T14:02:44.567413',
        }
    )
    person.save_to_popit(mock_api)

    return mock_api, mocked_post, person


class TestCreatePerson(TestUserMixin, WebTest):

    def test_create_jane_doe(self):

        mock_api, mocked_post, person = mock_create_person()
        # Then we expect one post, with the right data:
        self.assertEqual(1, len(mocked_post.call_args_list))
        self.assertTrue(
            equal_call_args(
                [EXPECTED_ARGS],
                mocked_post.call_args[0]
            ),
            "update_person was called with unexpected values"
        )
        self.assertEqual(1, mocked_post.call_count)
        self.assertFalse(mock_api.called)

    @patch('candidates.popit.PopIt')
    @patch.object(FakePersonCollection, 'post')
    @patch('candidates.models.popit.invalidate_posts')
    def test_create_from_post_page(
            self,
            mocked_invalidate_posts,
            mocked_post,
            mock_popit
    ):
        '''This is to check that posts are invalidated on creation'''

        mock_popit.return_value.persons = FakePersonCollection
        mock_popit.return_value.posts = FakePostCollection
        mocked_post.return_value = {'result': {'id': '789'}}
        response = self.app.get(
            '/election/2015/post/65808/dulwich-and-west-norwood',
            user=self.user,
        )
        form = response.forms['new-candidate-form']
        form['name'] = 'Elizabeth Bennet'
        form['email'] = 'lizzie@example.com'
        form['source'] = 'Testing adding a new person to a post'
        form['party_gb_2015'] = 'party:53'
        submission_response = form.submit()
        self.assertEqual(submission_response.status_code, 302)
        self.assertEqual(
            submission_response.location,
            'http://localhost:80/person/789'
        )
        # Check that the post the person is being added to has been
        # invalidated:
        self.assertEqual(mocked_invalidate_posts.call_count, 1)
        args = mocked_invalidate_posts.call_args_list[0][0]
        self.assertEqual(args, (set([u'65808']),))
        self.assertEqual(mocked_invalidate_posts.call_args_list[0][1], {})
