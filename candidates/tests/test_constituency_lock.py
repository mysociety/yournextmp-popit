from __future__ import unicode_literals

from mock import patch

from django_webtest import WebTest
from popolo.models import Person

from candidates.models import PostExtra

from .auth import TestUserMixin

from .factories import (
    AreaTypeFactory, ElectionFactory, PostExtraFactory,
    ParliamentaryChamberFactory, PersonExtraFactory,
    CandidacyExtraFactory, PartyExtraFactory,
    PartyFactory, PartySetFactory
)

class TestConstituencyLockAndUnlock(TestUserMixin, WebTest):

    def setUp(self):
        wmc_area_type = AreaTypeFactory.create()
        gb_parties = PartySetFactory.create(slug='gb', name='Great Britain')
        election = ElectionFactory.create(
            slug='2015',
            name='2015 General Election',
            area_types=(wmc_area_type,)
        )
        commons = ParliamentaryChamberFactory.create()
        post_extra = PostExtraFactory.create(
            candidates_locked=False,
            elections=(election,),
            base__organization=commons,
            slug='65808',
            base__label='Member of Parliament for Dulwich and West Norwood',
            party_set=gb_parties,
        )
        PostExtraFactory.create(
            candidates_locked=True,
            elections=(election,),
            base__organization=commons,
            slug='65913',
            base__label='Member of Parliament for Camberwell and Peckham',
            party_set=gb_parties,
        )
        self.post_extra_id = post_extra.id

    def test_constituency_lock_unauthorized(self):
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

    def test_constituency_lock_bad_submission(self):
        post_extra = PostExtra.objects.get(id=self.post_extra_id)
        post_extra.candidates_locked = False
        post_extra.save()
        self.app.get(
            '/election/2015/post/65808/dulwich-and-west-norwood',
            user=self.user_who_can_lock,
        )
        csrftoken = self.app.cookies['csrftoken']
        with self.assertRaises(Exception) as context:
            response = self.app.post(
                '/election/2015/post/lock',
                {
                    'csrfmiddlewaretoken': csrftoken,
                },
                user=self.user_who_can_lock,
                expect_errors=True,
            )

            self.assertTrue('Invalid data POSTed' in context.exception)

    def test_constituency_lock(self):
        post_extra = PostExtra.objects.get(id=self.post_extra_id)
        post_extra.candidates_locked = False
        post_extra.save()
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
        post_extra.refresh_from_db()
        self.assertEqual(True, post_extra.candidates_locked)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(
            response.location,
            "http://localhost:80/election/2015/post/65808/dulwich-and-west-norwood"
        )

    def test_constituency_unlock(self):
        post_extra = PostExtra.objects.get(id=self.post_extra_id)
        post_extra.candidates_locked = True
        post_extra.save()
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
        post_extra.refresh_from_db()
        self.assertEqual(False, post_extra.candidates_locked)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(
            response.location,
            "http://localhost:80/election/2015/post/65808/dulwich-and-west-norwood"
        )

    def test_constituencies_unlocked_list(self):
        response = self.app.get(
            '/election/2015/constituencies/unlocked',
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn('Dulwich', response.text)
        self.assertNotIn('Camberwell', response.text)


class TestConstituencyLockWorks(TestUserMixin, WebTest):

    def setUp(self):
        wmc_area_type = AreaTypeFactory.create()
        gb_parties = PartySetFactory.create(slug='gb', name='Great Britain')
        self.election = ElectionFactory.create(
            slug='2015',
            name='2015 General Election',
            area_types=(wmc_area_type,)
        )
        self.commons = ParliamentaryChamberFactory.create()
        PartyExtraFactory.reset_sequence()
        PartyFactory.reset_sequence()
        self.parties = {}
        for i in range(0, 4):
            party_extra = PartyExtraFactory.create()
            gb_parties.parties.add(party_extra.base)
            self.parties[party_extra.slug] = party_extra
        post_extra = PostExtraFactory.create(
            candidates_locked=False,
            elections=(self.election,),
            base__organization=self.commons,
            slug='65808',
            base__label='Member of Parliament for Dulwich and West Norwood',
            party_set=gb_parties,
        )
        post_extra_locked = PostExtraFactory.create(
            candidates_locked=True,
            elections=(self.election,),
            base__organization=self.commons,
            slug='65913',
            base__label='Member of Parliament for Camberwell and Peckham',
            party_set=gb_parties,
        )
        self.post_extra_id = post_extra.id
        person_extra = PersonExtraFactory.create(
            base__id='4170',
            base__name='Naomi Newstead'
        )

        CandidacyExtraFactory.create(
            election=self.election,
            base__person=person_extra.base,
            base__post=post_extra_locked.base,
            base__on_behalf_of=self.parties['party:63'].base
        )

        person_extra = PersonExtraFactory.create(
            base__id='4322',
            base__name='Helen Hayes'
        )

        CandidacyExtraFactory.create(
            election=self.election,
            base__person=person_extra.base,
            base__post=post_extra.base,
            base__on_behalf_of=self.parties['party:63'].base
        )

    def test_add_when_locked_unprivileged_disallowed(self):
        # Just get that page for the csrftoken cookie; the form won't
        # appear on the page, since the constituency is locked:
        response = self.app.get(
            '/election/2015/post/65913/camberwell-and-peckham',
            user=self.user
        )
        csrftoken = self.app.cookies['csrftoken']
        response = self.app.post(
            '/election/2015/person/create/',
            {
                'csrfmiddlewaretoken': csrftoken,
                'name': 'Imaginary Candidate',
                'party_gb_2015': self.parties['party:63'].base_id,
                'constituency_2015': '65913',
                'standing_2015': 'standing',
                'source': 'Testing adding a new candidate to a locked constituency',
            },
            expect_errors=True,
        )
        self.assertEqual(response.status_code, 403)

    def test_add_when_locked_privileged_allowed(self):
        response = self.app.get(
            '/election/2015/post/65913/camberwell-and-peckham',
            user=self.user_who_can_lock
        )
        form = response.forms['new-candidate-form']
        form['name'] = "Imaginary Candidate"
        form['party_gb_2015'] = self.parties['party:63'].base_id
        form['source'] = 'Testing adding a new candidate to a locked constituency'
        submission_response = form.submit()
        self.assertEqual(submission_response.status_code, 302)
        # Find the person this should have redirected to:
        expected_person = Person.objects.get(name='Imaginary Candidate')
        self.assertEqual(
            submission_response.location,
            'http://localhost:80/person/{0}'.format(expected_person.id)
        )

    def test_move_into_locked_unprivileged_disallowed(self):
        response = self.app.get(
            '/person/4322/update',
            user=self.user
        )
        form = response.forms['person-details']
        form['source'] = 'Testing a switch to a locked constituency'
        form['constituency_2015'] = '65913'
        submission_response = form.submit(expect_errors=True)
        self.assertEqual(submission_response.status_code, 403)

    def test_move_into_locked_privileged_allowed(self):
        response = self.app.get(
            '/person/4322/update',
            user=self.user_who_can_lock
        )
        form = response.forms['person-details']
        form['source'] = 'Testing a switch to a locked constituency'
        form['constituency_2015'] = '65913'
        submission_response = form.submit()
        self.assertEqual(submission_response.status_code, 302)
        self.assertEqual(
            submission_response.location,
            'http://localhost:80/person/4322'
        )

    def test_move_out_of_locked_unprivileged_disallowed(self):
        response = self.app.get(
            '/person/4170/update',
            user=self.user
        )
        form = response.forms['person-details']
        form['source'] = 'Testing a switch to a unlocked constituency'
        form['constituency_2015'] = '65808'
        submission_response = form.submit(expect_errors=True)
        self.assertEqual(submission_response.status_code, 403)

    def test_move_out_of_locked_privileged_allowed(self):
        response = self.app.get(
            '/person/4170/update',
            user=self.user_who_can_lock
        )
        form = response.forms['person-details']
        form['source'] = 'Testing a switch to a unlocked constituency'
        form['constituency_2015'] = '65808'
        submission_response = form.submit()
        self.assertEqual(submission_response.status_code, 302)
        self.assertEqual(
            submission_response.location,
            'http://localhost:80/person/4170'
        )

    # Now the tests to check that the only privileged users can change
    # the parties of people in locked constituecies.

    def test_change_party_in_locked_unprivileged_disallowed(self):
        response = self.app.get(
            '/person/4170/update',
            user=self.user
        )
        form = response.forms['person-details']
        form['source'] = 'Testing a party change in a locked constituency'
        form['party_gb_2015'] = self.parties['party:52'].base_id
        submission_response = form.submit(expect_errors=True)
        self.assertEqual(submission_response.status_code, 403)

    def test_change_party_in_locked_privileged_allowed(self):
        response = self.app.get(
            '/person/4170/update',
            user=self.user_who_can_lock
        )
        form = response.forms['person-details']
        form['source'] = 'Testing a party change in a locked constituency'
        form['party_gb_2015'] = self.parties['party:52'].base_id
        submission_response = form.submit()
        self.assertEqual(submission_response.status_code, 302)
        self.assertEqual(
            submission_response.location,
            'http://localhost:80/person/4170'
        )

    def test_change_party_in_unlocked_unprivileged_allowed(self):
        response = self.app.get(
            '/person/4322/update',
            user=self.user
        )
        form = response.forms['person-details']
        form['source'] = 'Testing a party change in an unlocked constituency'
        form['party_gb_2015'] = self.parties['party:52'].base_id
        submission_response = form.submit()
        self.assertEqual(submission_response.status_code, 302)
        self.assertEqual(
            submission_response.location,
            'http://localhost:80/person/4322'
        )
