from collections import defaultdict
from mock import patch

from django.core.urlresolvers import reverse
from django_webtest import WebTest

from .auth import TestUserMixin
from candidates.tests.fake_popit import (
    FakePostCollection, FakePersonCollection, FakeMembershipCollection
)


@patch('candidates.popit.PopIt')
class TestRecordWinner(TestUserMixin, WebTest):

    def test_record_winner_link_present(
            self,
            mock_popit
    ):
        mock_popit.return_value.posts = FakePostCollection
        response = self.app.get(
            '/constituency/65808/dulwich-and-west-norwood',
            user=self.user_who_can_record_results,
        )
        self.assertIn(
            'This candidate won!',
            unicode(response),
        )
        record_url = reverse(
            'record-winner',
            kwargs={'mapit_area_id': '65808'}
        )
        self.assertIn(
            record_url,
            unicode(response),
        )

    def test_record_winner_link_not_present(
            self,
            mock_popit
    ):
        mock_popit.return_value.posts = FakePostCollection
        response = self.app.get(
            '/constituency/65808/dulwich-and-west-norwood',
            user=self.user,
        )
        self.assertNotIn(
            'This candidate won!',
            unicode(response)
        )

    @patch.object(FakePersonCollection, 'put')
    @patch.object(FakePostCollection, 'put')
    def test_record_winner_not_privileged(
            self,
            mocked_post_put,
            mocked_person_put,
            mock_popit
    ):
        mock_popit.return_value.persons = FakePersonCollection
        mock_popit.return_value.posts = FakePostCollection
        # Get the constituency page just to set the CSRF token
        self.app.get(
            '/constituency/65808/dulwich-and-west-norwood',
            user=self.user,
        )
        csrftoken = self.app.cookies['csrftoken']
        base_record_url = reverse(
            'record-winner',
            kwargs={'mapit_area_id': '65808'}
        )
        form_get_response = self.app.get(
            base_record_url + '?person=4322',
            expect_errors=True,
        )
        self.assertEqual(form_get_response.status_code, 403)
        post_response = self.app.post(
            base_record_url,
            {
                'csrfmiddlewaretoken': csrftoken,
                'person_id': '4322',
                'source': 'BBC news',
            },
            expect_errors=True,
        )
        self.assertEqual(post_response.status_code, 403)
        self.assertFalse(mocked_person_put.called)

    @patch('candidates.models.popit.invalidate_posts')
    @patch('candidates.models.popit.invalidate_person')
    @patch.object(FakePersonCollection, 'put')
    @patch.object(FakePostCollection, 'put')
    def test_record_winner_non_incumbent_with_parlparse_id_privileged(
            self,
            mocked_post_put,
            mocked_person_put,
            mock_invalidate_person,
            mock_invalidate_posts,
            mock_popit
    ):
        mock_popit.return_value.persons = FakePersonCollection
        mock_popit.return_value.posts = FakePostCollection
        base_record_url = reverse(
            'record-winner',
            kwargs={'mapit_area_id': '65808'}
        )
        form_get_response = self.app.get(
            base_record_url + '?person=4322',
            user=self.user_who_can_record_results,
            expect_errors=True,
        )
        form = form_get_response.forms[0]
        self.assertEqual(form_get_response.status_code, 200)
        form['source'] = 'BBC website'
        submission_response = form.submit()
        self.assertEqual(submission_response.status_code, 302)
        self.assertEqual(
            submission_response.location,
            'http://localhost:80/constituency/65808/dulwich-and-west-norwood',
        )
        self.assertFalse(mocked_post_put.called)
        # There's only one candidate marked as standing in 2015 (Helen
        # Hayes) so there should be two PUTs to her record (the first
        # being the FIXME purging PUT.
        self.assertEqual(mocked_person_put.call_count, 2)
        second_put_data = mocked_person_put.call_args_list[1][0][0]
        self.assertEqual(
            second_put_data['standing_in'],
            {
                '2015': {
                    'elected': True,
                    'mapit_url': u'http://mapit.mysociety.org/area/65808',
                    'name': u'Dulwich and West Norwood',
                    'post_id': u'65808',
                }
            }
        )

    @patch('candidates.models.popit.invalidate_posts')
    @patch('candidates.models.popit.invalidate_person')
    @patch.object(FakePersonCollection, 'put')
    @patch.object(FakePostCollection, 'put')
    def test_record_winner_non_incumbent_without_parlparse_id_privileged(
            self,
            mocked_post_put,
            mocked_person_put,
            mock_invalidate_person,
            mock_invalidate_posts,
            mock_popit
    ):
        mock_popit.return_value.persons = FakePersonCollection
        mock_popit.return_value.posts = FakePostCollection
        base_record_url = reverse(
            'record-winner',
            kwargs={'mapit_area_id': '65808'}
        )
        form_get_response = self.app.get(
            base_record_url + '?person=4322',
            user=self.user_who_can_record_results,
            expect_errors=True,
        )
        form = form_get_response.forms[0]
        self.assertEqual(form_get_response.status_code, 200)
        form['source'] = 'BBC website'
        submission_response = form.submit()
        self.assertEqual(submission_response.status_code, 302)
        self.assertEqual(
            submission_response.location,
            'http://localhost:80/constituency/65808/dulwich-and-west-norwood',
        )
        self.assertFalse(mocked_post_put.called)
        # There's only one candidate marked as standing in 2015 (Helen
        # Hayes) so there should be two PUTs to her record (the first
        # being the FIXME purging PUT.
        self.assertEqual(mocked_person_put.call_count, 2)
        second_put_data = mocked_person_put.call_args_list[1][0][0]
        self.assertEqual(
            second_put_data['standing_in'],
            {
                '2015': {
                    'elected': True,
                    'mapit_url': u'http://mapit.mysociety.org/area/65808',
                    'name': u'Dulwich and West Norwood',
                    'post_id': u'65808',
                }
            }
        )
        self.assertEqual(second_put_data['identifiers'], [])

    maxDiff = None

    @patch('candidates.models.popit.invalidate_posts')
    @patch('candidates.models.popit.invalidate_person')
    @patch.object(FakePersonCollection, 'put')
    @patch.object(FakePostCollection, 'put')
    @patch.object(FakeMembershipCollection, 'post')
    @patch.object(FakeMembershipCollection, 'delete')
    def test_record_winner_was_incumbent_privileged(
            self,
            mocked_membership_delete,
            mocked_membership_post,
            mocked_post_put,
            mocked_person_put,
            mock_invalidate_person,
            mock_invalidate_posts,
            mock_popit
    ):
        mock_popit.return_value.persons = FakePersonCollection
        mock_popit.return_value.posts = FakePostCollection
        mock_popit.return_value.memberships = FakeMembershipCollection
        base_record_url = reverse(
            'record-winner',
            kwargs={'mapit_area_id': '65735'}
        )
        form_get_response = self.app.get(
            base_record_url + '?person=2422',
            user=self.user_who_can_record_results,
            expect_errors=True,
        )
        form = form_get_response.forms[0]
        self.assertEqual(form_get_response.status_code, 200)
        form['source'] = 'BBC website'
        submission_response = form.submit()
        self.assertEqual(submission_response.status_code, 302)
        self.assertEqual(
            submission_response.location,
            'http://localhost:80/constituency/65735/morley-and-outwood',
        )
        self.assertFalse(mocked_post_put.called)
        # There are 6 candidates standing in Morley and Outwood, so
        # there should be two PUTs for each:
        self.assertEqual(mocked_person_put.call_count, 12)
        # Just keep the second of each PUTs, keyed by name:
        put_data_by_person = {}
        for call in mocked_person_put.call_args_list:
            data = call[0][0]
            put_data_by_person[data['name']] = data
        self.assertEqual(
            put_data_by_person['Ed Balls']['standing_in'],
            {
                '2010': {
                    'mapit_url': 'http://mapit.mysociety.org/area/65735',
                    'name': 'Morley and Outwood',
                    'post_id': '65735',
                },
                '2015': {
                    'elected': True,
                    'mapit_url': 'http://mapit.mysociety.org/area/65735',
                    'name': 'Morley and Outwood',
                    'post_id': '65735',
                }
            }
        )
        self.assertEqual(
            put_data_by_person['Ed Balls']['identifiers'],
            [
                {
                    'id': '55350da616edb65574ea9eab',
                    'identifier': '3561',
                    'scheme': 'yournextmp-candidate'
                },
                {
                    'id': '55350da616edb65574ea9eaa',
                    'scheme': 'uk.org.publicwhip',
                    'identifier': 'uk.org.publicwhip/person/11740'
                }
            ]
        )
        membership_posts_by_person_id = defaultdict(list)
        for call in mocked_membership_post.call_args_list:
            data = call[0][0]
            membership_posts_by_person_id[data['person_id']].append(data)

        # Ed Balls should now be created with 5 memberships, 2 party,
        # 2 candidacy, and 1 member of parliament for the new
        # parliament:
        balls_memberships = membership_posts_by_person_id['2422']
        self.assertEqual(len(balls_memberships), 5)
        # Check that the MP memberships is right:
        mp_memberships = [
            m for m in balls_memberships if m.get('organization_id') == 'commons'
        ]
        self.assertEqual(len(mp_memberships), 1)
        self.assertEqual(
            mp_memberships[0],
            {
                'end_date': '9999-12-31',
                'organization_id': 'commons',
                'person_id': u'2422',
                'post_id': u'65735',
                'start_date': '2015-05-08'
            }
        )
        # Also check that someone who didn't win is set as not
        # elected:
        self.assertEqual(
            put_data_by_person['Rebecca Taylor']['standing_in'],
            {
                '2010': {
                    'mapit_url': 'http://mapit.mysociety.org/area/66029',
                    'name': 'Rotherham',
                    'post_id': '66029',
                },
                '2015': {
                    'elected': False,
                    'mapit_url': 'http://mapit.mysociety.org/area/65735',
                    'name': 'Morley and Outwood',
                    'post_id': '65735',
                }
            }
        )
