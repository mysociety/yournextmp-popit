from django.contrib.auth.models import User

from django_webtest import WebTest

from .auth import TestUserMixin
from ..models import LoggedAction

class TestLeaderboardView(TestUserMixin, WebTest):

    def setUp(self):
        self.user2 = User.objects.create_user(
            'jane',
            'jane@example.com',
            'notagoodpassword',
        )
        self.action1 = LoggedAction.objects.create(
            user=self.user,
            action_type='person-create',
            ip_address='127.0.0.1',
            popit_person_id='9876',
            popit_person_new_version='1234567890abcdef',
            source='Just for tests...',
        )
        self.action2 = LoggedAction.objects.create(
            user=self.user2,
            action_type='candidacy-delete',
            ip_address='127.0.0.1',
            popit_person_id='1234',
            popit_person_new_version='987654321',
            source='Also just for testing',
        )
        self.action2 = LoggedAction.objects.create(
            user=self.user2,
            action_type='candidacy-delete',
            ip_address='127.0.0.1',
            popit_person_id='1234',
            popit_person_new_version='987654321',
            source='Also just for testing',
        )

    def tearDown(self):
        self.action2.delete()
        self.action1.delete()
        self.user2.delete()

    def test_recent_changes_page(self):
        # Just a smoke test to check that the page loads:
        response = self.app.get('/leaderboard')
        table = response.html.find('table')
        rows = table.find_all('tr')
        self.assertEqual(3, len(rows))
        first_row = rows[1]
        cells = first_row.find_all('td')
        self.assertEqual(cells[0].text, self.user2.username)
        second_row = rows[2]
        cells = second_row.find_all('td')
        self.assertEqual(cells[0].text, self.user.username)

    def test_get_contributions_csv(self):
        response = self.app.get('/leaderboard/contributions.csv')
        self.assertEqual(
            response.body,
            'rank,username,contributions\r\n' +
                '0,jane,2\r\n' +
                '1,john,1\r\n' +
                '2,alice,0\r\n' +
                '3,charles,0\r\n' +
                '4,delilah,0\r\n' +
                '5,ermintrude,0\r\n' +
                '6,frankie,0\r\n' +
                '7,johnrefused,0\r\n'
        )
