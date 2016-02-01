from __future__ import unicode_literals

from django_webtest import WebTest
from django.test.utils import override_settings

from .auth import TestUserMixin
from .factories import PersonExtraFactory

# FIXME: these pass individually but fail together because of
# https://github.com/django-compressor/django-appconf/issues/30

class TestRenameRestriction(TestUserMixin, WebTest):

    def setUp(self):
        PersonExtraFactory.create(
            base__id=4322,
            base__name='Helen Hayes',
            base__email='hayes@example.com',
        )

    @override_settings(RESTRICT_RENAMES=True)
    def test_renames_restricted_unprivileged(self):
        response = self.app.get(
            '/person/4322/update',
            user=self.user
        )
        form = response.forms['person-details']
        form['name'] = 'Ms Helen Hayes'
        form['source'] = 'Testing renaming'
        submission_response = form.submit(expect_errors=True)
        self.assertEqual(submission_response.status_code, 302)
        self.assertEqual(
            submission_response.location,
            'http://localhost:80/update-disallowed',
        )

    @override_settings(RESTRICT_RENAMES=True)
    def test_renames_restricted_privileged(self):
        response = self.app.get(
            '/person/4322/update',
            user=self.user_who_can_rename,
        )
        form = response.forms['person-details']
        form['name'] = 'Ms Helen Hayes'
        form['source'] = 'Testing renaming'
        submission_response = form.submit(expect_errors=True)
        self.assertEqual(submission_response.status_code, 302)
        self.assertEqual(
            submission_response.location,
            'http://localhost:80/person/4322',
        )

    def test_renames_unrestricted_unprivileged(self):
        response = self.app.get(
            '/person/4322/update',
            user=self.user,
        )
        form = response.forms['person-details']
        form['name'] = 'Ms Helen Hayes'
        form['source'] = 'Testing renaming'
        submission_response = form.submit(expect_errors=True)
        self.assertEqual(submission_response.status_code, 302)
        self.assertEqual(
            submission_response.location,
            'http://localhost:80/person/4322',
        )

    def test_renames_unrestricted_privileged(self):
        response = self.app.get(
            '/person/4322/update',
            user=self.user,
        )
        form = response.forms['person-details']
        form['name'] = 'Ms Helen Hayes'
        form['source'] = 'Testing renaming'
        submission_response = form.submit(expect_errors=True)
        self.assertEqual(submission_response.status_code, 302)
        self.assertEqual(
            submission_response.location,
            'http://localhost:80/person/4322',
        )
