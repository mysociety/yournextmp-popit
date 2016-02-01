 # -*- coding: utf-8 -*-

from __future__ import unicode_literals

from django_webtest import WebTest

from .auth import TestUserMixin
from ..models import LoggedAction

class TestFeeds(TestUserMixin, WebTest):

    def setUp(self):
        self.action1 = LoggedAction.objects.create(
            user=self.user,
            action_type='person-create',
            ip_address='127.0.0.1',
            person_id='9876',
            popit_person_new_version='1234567890abcdef',
            source='Just for tests...',
        )
        self.action2 = LoggedAction.objects.create(
            user=self.user,
            action_type='candidacy-delete',
            ip_address='127.0.0.1',
            person_id='1234',
            popit_person_new_version='987654321',
            source='Something with unicode in it…',
        )

    def test_unicode(self):
        response = self.app.get('/feeds/changes.xml')
        self.assertTrue("Just for tests..." in response)
        self.assertTrue("Something with unicode in it…" in response)

    def tearDown(self):
        self.action2.delete()
        self.action1.delete()
