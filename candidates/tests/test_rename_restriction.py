from mock import patch

from django_webtest import WebTest
from django.test.utils import override_settings

from .auth import TestUserMixin
from .fake_popit import FakePersonCollection, FakePostCollection

@patch('candidates.popit.PopIt')
class TestRenameRestriction(TestUserMixin, WebTest):

    @override_settings(RESTRICT_RENAMES=True)
    @patch.object(FakePersonCollection, 'put')
    def test_renames_restricted_unprivileged(self, mocked_put, mock_popit):
        mock_popit.return_value.persons = FakePersonCollection
        mock_popit.return_value.posts = FakePostCollection
        response = self.app.get(
            '/person/4322/update',
            user=self.user
        )
        form = response.forms['person-details']
        form['name'] = 'Ms Helen Hayes'
        form['source'] = 'Testing renaming'
        submission_response = form.submit(expect_errors=True)
        self.assertFalse(mocked_put.called)
        self.assertEqual(submission_response.status_code, 302)
        self.assertEqual(
            submission_response.location,
            'http://localhost:80/update-disallowed',
        )

    @override_settings(RESTRICT_RENAMES=True)
    @patch.object(FakePersonCollection, 'put')
    def test_renames_restricted_privileged(self, mocked_put, mock_popit):
        mock_popit.return_value.persons = FakePersonCollection
        mock_popit.return_value.posts = FakePostCollection
        response = self.app.get(
            '/person/4322/update',
            user=self.user_who_can_rename,
        )
        form = response.forms['person-details']
        form['name'] = 'Ms Helen Hayes'
        form['source'] = 'Testing renaming'
        submission_response = form.submit(expect_errors=True)
        self.assertEqual(mocked_put.call_count, 2)
        self.assertEqual(submission_response.status_code, 302)
        self.assertEqual(
            submission_response.location,
            'http://localhost:80/person/4322',
        )

    @patch.object(FakePersonCollection, 'put')
    def test_renames_unrestricted_unprivileged(self, mocked_put, mock_popit):
        mock_popit.return_value.persons = FakePersonCollection
        mock_popit.return_value.posts = FakePostCollection
        response = self.app.get(
            '/person/4322/update',
            user=self.user,
        )
        form = response.forms['person-details']
        form['name'] = 'Ms Helen Hayes'
        form['source'] = 'Testing renaming'
        submission_response = form.submit(expect_errors=True)
        self.assertEqual(mocked_put.call_count, 2)
        self.assertEqual(submission_response.status_code, 302)
        self.assertEqual(
            submission_response.location,
            'http://localhost:80/person/4322',
        )

    @patch.object(FakePersonCollection, 'put')
    def test_renames_unrestricted_privileged(self, mocked_put, mock_popit):
        mock_popit.return_value.persons = FakePersonCollection
        mock_popit.return_value.posts = FakePostCollection

        response = self.app.get(
            '/person/4322/update',
            user=self.user,
        )
        form = response.forms['person-details']
        form['name'] = 'Ms Helen Hayes'
        form['source'] = 'Testing renaming'
        submission_response = form.submit(expect_errors=True)
        self.assertEqual(mocked_put.call_count, 2)
        self.assertEqual(submission_response.status_code, 302)
        self.assertEqual(
            submission_response.location,
            'http://localhost:80/person/4322',
        )
