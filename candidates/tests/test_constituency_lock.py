from mock import patch

from django_webtest import WebTest

from .auth import TestUserMixin
from candidates.tests.fake_popit import (
    FakePostCollection, FakePersonCollection, fake_mp_post_search_results
)

@patch('candidates.popit.PopIt')
@patch('candidates.popit.requests')
class TestConstituencyLockAndUnlock(TestUserMixin, WebTest):

    def test_constituency_lock_unauthorized(self, mock_requests, mock_popit):
        mock_popit.return_value.posts = FakePostCollection
        mock_requests.get.side_effect = fake_mp_post_search_results
        self.app.get(
            '/election/2015/post/65808/dulwich-and-west-norwood',
            user=self.user,
        )
        csrftoken = self.app.cookies['csrftoken']
        response = self.app.post(
            '/election/2015/post/lock',
            {
                'lock': 'True',
                'post_id': '65808',
                'csrfmiddlewaretoken': csrftoken,
            },
            user=self.user,
            expect_errors=True,
        )
        self.assertEqual(response.status_code, 403)

    @patch.object(FakePostCollection, 'put')
    def test_constituency_lock(self, mocked_put, mock_requests, mock_popit):
        mock_popit.return_value.posts = FakePostCollection
        mock_requests.get.side_effect = fake_mp_post_search_results
        self.app.get(
            '/election/2015/post/65808/dulwich-and-west-norwood',
            user=self.user_who_can_lock,
        )
        csrftoken = self.app.cookies['csrftoken']
        response = self.app.post(
            '/election/2015/post/lock',
            {
                'lock': 'True',
                'post_id': '65808',
                'csrfmiddlewaretoken': csrftoken,
            },
            user=self.user_who_can_lock,
            expect_errors=True,
        )
        expected_put = {
            u'organization_id': u'commons',
            u'contact_details': [],
            u'links': [],
            u'area': {
                u'identifier': u'http://mapit.mysociety.org/area/65808',
                u'name': u'Dulwich and West Norwood',
                u'id': u'mapit:65808'
            },
            u'url': u'http://candidates.127.0.0.1.xip.io:3000/api/v0.1/posts/65808',
            u'id': u'65808',
            u'html_url': u'http://candidates.127.0.0.1.xip.io:3000/posts/65808',
            u'label': u'Member of Parliament for Dulwich and West Norwood',
            u'memberships': [],
            u'candidates_locked': True,
            u'role': u'Member of Parliament',
            u'images': [],
            u'start_date': u'2005-05-06'
        }
        self.assertEqual(
            (expected_put,),
            mocked_put.call_args_list[0][0]
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(
            response.location,
            "http://localhost:80/election/2015/post/65808/dulwich-and-west-norwood"
        )

    @patch.object(FakePostCollection, 'put')
    def test_constituency_unlock(self, mocked_put, mock_requests, mock_popit):
        mock_popit.return_value.posts = FakePostCollection
        mock_requests.get.side_effect = fake_mp_post_search_results
        self.app.get(
            '/election/2015/post/65808/dulwich-and-west-norwood',
            user=self.user_who_can_lock,
        )
        csrftoken = self.app.cookies['csrftoken']
        response = self.app.post(
            '/election/2015/post/lock',
            {
                'lock': 'False',
                'post_id': '65808',
                'csrfmiddlewaretoken': csrftoken,
            },
            user=self.user_who_can_lock,
            expect_errors=True,
        )
        expected_put = {
            u'organization_id': u'commons',
            u'contact_details': [],
            u'links': [],
            u'area': {
                u'identifier': u'http://mapit.mysociety.org/area/65808',
                u'name': u'Dulwich and West Norwood',
                u'id': u'mapit:65808'
            },
            u'url': u'http://candidates.127.0.0.1.xip.io:3000/api/v0.1/posts/65808',
            u'id': u'65808',
            u'html_url': u'http://candidates.127.0.0.1.xip.io:3000/posts/65808',
            u'label': u'Member of Parliament for Dulwich and West Norwood',
            u'memberships': [],
            u'candidates_locked': False,
            u'role': u'Member of Parliament',
            u'images': [],
            u'start_date': u'2005-05-06'
        }
        self.assertEqual(
            (expected_put,),
            mocked_put.call_args_list[0][0]
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(
            response.location,
            "http://localhost:80/election/2015/post/65808/dulwich-and-west-norwood"
        )

    def test_constituencies_unlocked_list(self, mock_requests, mock_popit):
        mock_popit.return_value.posts = FakePostCollection
        mock_requests.get.side_effect = fake_mp_post_search_results
        response = self.app.get(
            '/election/2015/constituencies/unlocked',
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn('Dulwich', unicode(response))
        self.assertNotIn('Camberwell', unicode(response))

@patch('candidates.popit.PopIt')
@patch('candidates.popit.requests')
class TestConstituencyLockWorks(TestUserMixin, WebTest):

    @patch.object(FakePersonCollection, 'post')
    def test_add_when_locked_unprivileged_disallowed(
            self, mocked_post, mock_requests, mock_popit
    ):
        mock_popit.return_value.persons = FakePersonCollection
        mock_popit.return_value.posts = FakePostCollection
        mock_requests.get.side_effect = fake_mp_post_search_results
        # Just get that page for the csrftoken cookie; the form won't
        # appear on the page, since the constituency is locked:
        response = self.app.get(
            '/election/2015/post/65913/camberwell-and-peckham',
            user=self.user
        )
        csrftoken = self.app.cookies['csrftoken']
        mocked_post.return_value = {'result': {'id': '1234'}}
        response = self.app.post(
            '/election/2015/person/create/',
            {
                'csrfmiddlewaretoken': csrftoken,
                'name': 'Imaginary Candidate',
                'party_gb_2015': 'party:63',
                'constituency_2015': '65913',
                'standing_2015': 'standing',
                'source': 'Testing adding a new candidate to a locked constituency',
            },
            expect_errors=True,
        )
        self.assertFalse(mocked_post.called)
        self.assertEqual(response.status_code, 403)

    @patch.object(FakePersonCollection, 'post')
    def test_add_when_locked_privileged_allowed(
            self, mocked_post, mock_requests, mock_popit
    ):
        mock_popit.return_value.persons = FakePersonCollection
        mock_popit.return_value.posts = FakePostCollection
        mock_requests.get.side_effect = fake_mp_post_search_results
        mocked_post.return_value = {'result': {'id': '1234'}}
        response = self.app.get(
            '/election/2015/post/65913/camberwell-and-peckham',
            user=self.user_who_can_lock
        )
        form = response.forms['new-candidate-form']
        form['name'] = "Imaginary Candidate"
        form['party_gb_2015'] = 'party:63'
        form['source'] = 'Testing adding a new candidate to a locked constituency'
        submission_response = form.submit()
        self.assertEqual(mocked_post.call_count, 1)
        self.assertEqual(submission_response.status_code, 302)
        self.assertEqual(
            submission_response.location,
            'http://localhost:80/person/1234'
)

    @patch.object(FakePersonCollection, 'put')
    def test_move_into_locked_unprivileged_disallowed(
            self, mocked_put, mock_requests, mock_popit
    ):
        mock_popit.return_value.persons = FakePersonCollection
        mock_popit.return_value.posts = FakePostCollection
        mock_requests.get.side_effect = fake_mp_post_search_results
        response = self.app.get(
            '/person/4322/update',
            user=self.user
        )
        form = response.forms['person-details']
        form['source'] = 'Testing a switch to a locked constituency'
        form['constituency_2015'] = '65913'
        submission_response = form.submit(expect_errors=True)
        self.assertFalse(mocked_put.called)
        self.assertEqual(submission_response.status_code, 403)

    @patch.object(FakePersonCollection, 'put')
    def test_move_into_locked_privileged_allowed(
            self, mocked_put, mock_requests, mock_popit
    ):
        mock_popit.return_value.persons = FakePersonCollection
        mock_popit.return_value.posts = FakePostCollection
        mock_requests.get.side_effect = fake_mp_post_search_results
        response = self.app.get(
            '/person/4322/update',
            user=self.user_who_can_lock
        )
        form = response.forms['person-details']
        form['source'] = 'Testing a switch to a locked constituency'
        form['constituency_2015'] = '65913'
        submission_response = form.submit()
        self.assertEqual(mocked_put.call_count, 2)
        self.assertEqual(submission_response.status_code, 302)
        self.assertEqual(
            submission_response.location,
            'http://localhost:80/person/4322'
        )

    @patch.object(FakePersonCollection, 'put')
    def test_move_out_of_locked_unprivileged_disallowed(
            self, mocked_put, mock_requests, mock_popit
    ):
        mock_popit.return_value.persons = FakePersonCollection
        mock_popit.return_value.posts = FakePostCollection
        mock_requests.get.side_effect = fake_mp_post_search_results
        response = self.app.get(
            '/person/4170/update',
            user=self.user
        )
        form = response.forms['person-details']
        form['source'] = 'Testing a switch to a unlocked constituency'
        form['constituency_2015'] = '65808'
        submission_response = form.submit(expect_errors=True)
        self.assertFalse(mocked_put.called)
        self.assertEqual(submission_response.status_code, 403)

    @patch.object(FakePersonCollection, 'put')
    def test_move_out_of_locked_privileged_allowed(
            self, mocked_put, mock_requests, mock_popit
    ):
        mock_popit.return_value.persons = FakePersonCollection
        mock_popit.return_value.posts = FakePostCollection
        mock_requests.get.side_effect = fake_mp_post_search_results
        response = self.app.get(
            '/person/4170/update',
            user=self.user_who_can_lock
        )
        form = response.forms['person-details']
        form['source'] = 'Testing a switch to a unlocked constituency'
        form['constituency_2015'] = '65808'
        submission_response = form.submit()
        self.assertEqual(mocked_put.call_count, 2)
        self.assertEqual(submission_response.status_code, 302)
        self.assertEqual(
            submission_response.location,
            'http://localhost:80/person/4170'
        )

    # Now the tests to check that the only privileged users can change
    # the parties of people in locked constituecies.

    @patch.object(FakePersonCollection, 'put')
    def test_change_party_in_locked_unprivileged_disallowed(
            self, mocked_put, mock_requests, mock_popit
    ):
        mock_popit.return_value.persons = FakePersonCollection
        mock_popit.return_value.posts = FakePostCollection
        mock_requests.get.side_effect = fake_mp_post_search_results
        response = self.app.get(
            '/person/4170/update',
            user=self.user
        )
        form = response.forms['person-details']
        form['source'] = 'Testing a party change in a locked constituency'
        form['party_gb_2015'] = 'party:66'
        submission_response = form.submit(expect_errors=True)
        self.assertFalse(mocked_put.called)
        self.assertEqual(submission_response.status_code, 403)

    @patch.object(FakePersonCollection, 'put')
    def test_change_party_in_locked_privileged_allowed(
            self, mocked_put, mock_requests, mock_popit
    ):
        mock_popit.return_value.persons = FakePersonCollection
        mock_popit.return_value.posts = FakePostCollection
        mock_requests.get.side_effect = fake_mp_post_search_results
        response = self.app.get(
            '/person/4170/update',
            user=self.user_who_can_lock
        )
        form = response.forms['person-details']
        form['source'] = 'Testing a party change in a locked constituency'
        form['party_gb_2015'] = 'party:66'
        submission_response = form.submit()
        self.assertEqual(mocked_put.call_count, 2)
        self.assertEqual(submission_response.status_code, 302)
        self.assertEqual(
            submission_response.location,
            'http://localhost:80/person/4170'
        )

    @patch.object(FakePersonCollection, 'put')
    def test_change_party_in_unlocked_unprivileged_allowed(
            self, mocked_put, mock_requests, mock_popit
    ):
        mock_popit.return_value.persons = FakePersonCollection
        mock_popit.return_value.posts = FakePostCollection
        mock_requests.get.side_effect = fake_mp_post_search_results
        response = self.app.get(
            '/person/4322/update',
            user=self.user
        )
        form = response.forms['person-details']
        form['source'] = 'Testing a party change in an unlocked constituency'
        form['party_gb_2015'] = 'party:66'
        submission_response = form.submit()
        self.assertEqual(mocked_put.call_count, 2)
        self.assertEqual(submission_response.status_code, 302)
        self.assertEqual(
            submission_response.location,
            'http://localhost:80/person/4322'
        )
