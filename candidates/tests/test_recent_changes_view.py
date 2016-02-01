from __future__ import unicode_literals

from django_webtest import WebTest

from candidates.tests import factories

from .auth import TestUserMixin
from ..models import LoggedAction

class TestRecentChangesView(TestUserMixin, WebTest):

    def setUp(self):
        test_person_1 = factories.PersonExtraFactory.create(
            base__id=9876,
            base__name='Test Candidate for Recent Changes',
        )
        test_person_2 = factories.PersonExtraFactory.create(
            base__id=1234,
            base__name='Another Test Candidate for Recent Changes',
        )
        self.action1 = LoggedAction.objects.create(
            user=self.user,
            action_type='person-create',
            ip_address='127.0.0.1',
            person=test_person_1.base,
            popit_person_new_version='1234567890abcdef',
            source='Just for tests...',
        )
        self.action2 = LoggedAction.objects.create(
            user=self.user,
            action_type='candidacy-delete',
            ip_address='127.0.0.1',
            person=test_person_2.base,
            popit_person_new_version='987654321',
            source='Also just for testing',
        )

    def tearDown(self):
        self.action2.delete()
        self.action1.delete()

    def test_recent_changes_page(self):
        # Just a smoke test to check that the page loads:
        response = self.app.get('/recent-changes')
        table = response.html.find('table')
        self.assertEqual(3, len(table.find_all('tr')))
