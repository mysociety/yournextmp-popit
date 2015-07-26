# -*- coding: utf-8 -*-

from mock import patch
import re

from django_webtest import WebTest

from .auth import TestUserMixin
from .fake_popit import (FakePersonCollection, FakeOrganizationCollection,
                         FakePostCollection)


@patch('candidates.popit.PopIt')
class TestAreasView(TestUserMixin, WebTest):

    def test_any_area_page_without_login(self, mock_popit):
        mock_popit.return_value.organizations = FakeOrganizationCollection
        mock_popit.return_value.persons = FakePersonCollection
        mock_popit.return_value.posts = FakePostCollection

        response = self.app.get('/areas/WMC-65808/dulwich-and-west-norwood')
        self.assertEqual(response.status_code, 200)

        self.assertTrue(
            re.search(
                r'''(?msx)
  <h1>Areas:\s+Dulwich\s+and\s+West\s+Norwood</h1>.*
  <h3>Known\s+candidates\s+for\s*
  <a\s+href="/election/2015/post/65808/
  member-of-parliament-for-dulwich-and-west-norwood">
  Member\s+of\s+Parliament\s+for\s+Dulwich\s+and\s+West\s+Norwood</a>\s*
  </h3>''',
                unicode(response)
            )
        )

        # make sure there's at least one candidate
        self.assertTrue(
            response.html.find(
                'li', {'class': 'candidates-list__person'}
            )
        )


    def test_unlocked_area_without_login(self, mock_popit):
        mock_popit.return_value.organizations = FakeOrganizationCollection
        mock_popit.return_value.persons = FakePersonCollection
        mock_popit.return_value.posts = FakePostCollection

        response = self.app.get('/areas/WMC-65808/dulwich-and-west-norwood')

        # no editing functions should be visible
        self.assertNotIn('Add a new candidate', response)

        # should be invited to sign in to make edits
        self.assertIn('Sign in to edit', response)

        # no message about the data being locked should be visible
        self.assertFalse(
            re.search(
                r'''(?msx)
    <p>This\s+list\s+of\s+candidates\s+is\s+now\s+
    <strong>locked</strong>''',
                unicode(response)
            )
        )


    def test_locked_area_without_login(self, mock_popit):
        mock_popit.return_value.organizations = FakeOrganizationCollection
        mock_popit.return_value.persons = FakePersonCollection
        mock_popit.return_value.posts = FakePostCollection

        response = self.app.get('/areas/WMC-65913/camberwell-and-peckham')

        # no editing functions should be visible
        self.assertNotIn('Add a new candidate', response)

        # message about the data being locked should be visible
        self.assertTrue(
            re.search(
                r'''(?msx)
    <p>This\s+list\s+of\s+candidates\s+is\s+now\s+
    <strong>locked</strong>''',
                unicode(response)
            )
        )


    def test_unlocked_area_unauthorized(self, mock_popit):
        mock_popit.return_value.organizations = FakeOrganizationCollection
        mock_popit.return_value.persons = FakePersonCollection
        mock_popit.return_value.posts = FakePostCollection

        response = self.app.get(
            '/areas/WMC-65808/dulwich-and-west-norwood',
            user=self.user_refused
        )

        # should not be invited to add a new candidate
        self.assertNotIn('Add a new candidate', response)

        # should not be invited to sign in to make edits
        self.assertNotIn('Sign in to edit', response)

        # message about the data being locked should not be visible
        self.assertFalse(
            re.search(
                r'''(?msx)
    <p>This\s+list\s+of\s+candidates\s+is\s+now\s+
    <strong>locked</strong>''',
                unicode(response)
            )
        )


    def test_locked_area_unauthorized(self, mock_popit):
        mock_popit.return_value.organizations = FakeOrganizationCollection
        mock_popit.return_value.persons = FakePersonCollection
        mock_popit.return_value.posts = FakePostCollection

        response = self.app.get(
            '/areas/WMC-65913/camberwell-and-peckham',
            user=self.user_refused
        )

        # editing functions should not be visible
        self.assertNotIn('Add a new candidate', response)

        # should not be invited to sign in to make edits
        self.assertNotIn('Sign in to edit', response)

        # message about the data being locked should not be visible
        self.assertFalse(
            re.search(
                r'''(?msx)
    <p>This\s+list\s+of\s+candidates\s+is\s+now\s+
    <strong>locked</strong>''',
                unicode(response)
            )
        )


    def test_unlocked_area_edit_authorized(self, mock_popit):
        mock_popit.return_value.organizations = FakeOrganizationCollection
        mock_popit.return_value.persons = FakePersonCollection
        mock_popit.return_value.posts = FakePostCollection

        response = self.app.get(
            '/areas/WMC-65808/dulwich-and-west-norwood',
            user=self.user
        )

        # editing functions should be visible
        self.assertIn('Add a new candidate', response)

        # should not be invited to sign in to make edits
        self.assertNotIn('Sign in to edit', response)

        # message about the data being locked should not be visible
        self.assertFalse(
            re.search(
                r'''(?msx)
    <p>This\s+list\s+of\s+candidates\s+is\s+now\s+
    <strong>locked</strong>''',
                unicode(response)
            )
        )

        # option to lock the data should not be visible
        self.assertFalse(
            response.html.find(
                'input', {'value': 'Lock candidate list'}
            )
        )


    def test_locked_area_edit_authorized(self, mock_popit):
        mock_popit.return_value.organizations = FakeOrganizationCollection
        mock_popit.return_value.persons = FakePersonCollection
        mock_popit.return_value.posts = FakePostCollection

        response = self.app.get(
            '/areas/WMC-65913/camberwell-and-peckham',
            user=self.user
        )

        # editing functions should not be visible
        self.assertNotIn('Add a new candidate', response)

        # should not be invited to sign in to make edits
        self.assertNotIn('Sign in to edit', response)

        # message about the data being locked should be visible
        # at the top of the page
        self.assertTrue(
            re.search(
                r'''(?msx)
    <p>This\s+list\s+of\s+candidates\s+is\s+now\s+
    <strong>locked</strong>''',
                unicode(response)
            )
        )

        # option to unlock the data should not be visible
        self.assertFalse(
            response.html.find(
                'input', {'value': 'Unlock candidate list'}
            )
        )


    def test_unlocked_area_lock_authorized(self, mock_popit):
        mock_popit.return_value.organizations = FakeOrganizationCollection
        mock_popit.return_value.persons = FakePersonCollection
        mock_popit.return_value.posts = FakePostCollection

        response = self.app.get(
            '/areas/WMC-65808/dulwich-and-west-norwood',
            user=self.user_who_can_lock
        )

        # editing functions should be visible
        self.assertIn('Add a new candidate', response)

        # should not be invited to login to make edits
        self.assertNotIn('Sign in to edit', response)

        # message about the data being unlocked should be visible
        self.assertTrue(
            re.search(
                r'''(?msx)
            \(This\s+list\s+of\s+candidates\s+is\s+currently\s+
            <strong>unlocked</strong>.\)''',
                    unicode(response)
            )
        )

        # option to lock the data should be visible
        self.assertTrue(
            response.html.find(
                'input', {'value': 'Lock candidate list'}
            )
        )


    def test_locked_area_lock_authorized(self, mock_popit):
        mock_popit.return_value.organizations = FakeOrganizationCollection
        mock_popit.return_value.persons = FakePersonCollection
        mock_popit.return_value.posts = FakePostCollection

        response = self.app.get(
            '/areas/WMC-65913/camberwell-and-peckham',
            user=self.user_who_can_lock
        )

        # editing functions should be visible
        self.assertIn('Add a new candidate', response)

        # should not be invited to login to make edits
        self.assertNotIn('Sign in to edit', response)

        # message about the data being locked should be visible
        self.assertTrue(
            re.search(
                r'''(?msx)
    \(This\s+list\s+of\s+candidates\s+is\s+currently\s+
    <strong>locked</strong>.\)''',
                unicode(response)
            )
        )

        # option to unlock the data should be visible
        self.assertTrue(
            response.html.find(
                'input', {'value': 'Unlock candidate list'}
            )
        )


    def test_area_without_winner_record_result_authorized(self, mock_popit):
        mock_popit.return_value.organizations = FakeOrganizationCollection
        mock_popit.return_value.persons = FakePersonCollection
        mock_popit.return_value.posts = FakePostCollection

        response = self.app.get(
            '/areas/WMC-65913/camberwell-and-peckham',
            user=self.user_who_can_record_results
        )

        # should not allow recording the winner from this page
        self.assertNotIn('This candidate won!', response)


    def test_no_candidates_without_login(self, mock_popit):
        mock_popit.return_value.organizations = FakeOrganizationCollection
        mock_popit.return_value.persons = FakePersonCollection
        mock_popit.return_value.posts = FakePostCollection

        response = self.app.get('/areas/WMC-65730/aldershot')

        # should see the no candidates message
        self.assertIn('We don’t know of any candidates', response)

        # should be invited to sign in to add a candidate
        self.assertFalse(
            response.html.find(
                'a', {'text': 'Sign in to add a new candidate'}
            )
        )


    def test_no_candidates_with_login(self, mock_popit):
        mock_popit.return_value.organizations = FakeOrganizationCollection
        mock_popit.return_value.persons = FakePersonCollection
        mock_popit.return_value.posts = FakePostCollection

        response = self.app.get(
            '/areas/WMC-65730/aldershot',
            user=self.user
        )

        # should see the no candidates message
        self.assertIn('We don’t know of any candidates', response)

        # should be invited to add a candidate
        self.assertFalse(
            response.html.find(
                'a', {'text': 'Add a new candidate'}
            )
        )


    def test_get_malformed_url(self, mock_popit):
        response = self.app.get(
            '/areas/3243452345/invalid',
            expect_errors=True
        )
        self.assertEqual(response.status_code, 400)


    def test_get_non_existent(self, mock_popit):
        mock_popit.return_value.organizations = FakeOrganizationCollection
        mock_popit.return_value.posts = FakePostCollection
        response = self.app.get(
            '/areas/WMC-11111111/imaginary-constituency',
            expect_errors=True
        )
        self.assertEqual(response.status_code, 400)
