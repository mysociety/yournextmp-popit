# -*- coding: utf-8 -*-

from __future__ import unicode_literals

import json

from django.utils.six.moves.urllib_parse import urlsplit

from django_webtest import WebTest
from webtest.forms import Checkbox

from .auth import TestUserMixin
from .helpers import add_webtest_form_field

from popolo.models import Person

from candidates.models import ExtraField, PersonExtra
from candidates.models.auth import UnauthorizedAttemptToChangeMarkedForReview
from .factories import CandidacyExtraFactory, PersonExtraFactory
from .settings import SettingsMixin
from .uk_examples import UK2015ExamplesMixin


class TestUpdatePersonView(TestUserMixin, SettingsMixin, UK2015ExamplesMixin, WebTest):

    def setUp(self):
        super(TestUpdatePersonView, self).setUp()
        person_extra = PersonExtraFactory.create(
            base__id='2009',
            base__name='Tessa Jowell'
        )

        CandidacyExtraFactory.create(
            election=self.election,
            base__person=person_extra.base,
            base__post=self.dulwich_post_extra.base,
            base__on_behalf_of=self.green_party_extra.base
        )

    def test_update_person_view_get_without_login(self):
        response = self.app.get('/person/2009/update')
        self.assertEqual(response.status_code, 302)
        split_location = urlsplit(response.location)
        self.assertEqual('/accounts/login/', split_location.path)
        self.assertEqual('next=/person/2009/update', split_location.query)

    def test_update_person_view_get_refused_copyright(self):
        response = self.app.get('/person/2009/update', user=self.user_refused)
        self.assertEqual(response.status_code, 302)
        split_location = urlsplit(response.location)
        self.assertEqual('/copyright-question', split_location.path)
        self.assertEqual('next=/person/2009/update', split_location.query)

    def test_update_person_view_get(self):
        # For the moment just check that the form's actually there:
        response = self.app.get('/person/2009/update', user=self.user)
        form = response.forms['person-details']
        self.assertIsNotNone(form)

    def test_update_person_submission_copyright_refused(self):
        response = self.app.get('/person/2009/update', user=self.user)
        form = response.forms['person-details']
        form['wikipedia_url'] = 'http://en.wikipedia.org/wiki/Tessa_Jowell'
        form['party_gb_2015'] = self.labour_party_extra.base_id
        form['source'] = "Some source of this information"
        submission_response = form.submit(user=self.user_refused)
        split_location = urlsplit(submission_response.location)
        self.assertEqual('/copyright-question', split_location.path)
        self.assertEqual('next=/person/2009/update', split_location.query)

    def test_update_person_submission(self):
        response = self.app.get(
            '/person/2009/update',
            user=self.user_who_can_lock,
        )
        form = response.forms['person-details']
        form['wikipedia_url'] = 'http://en.wikipedia.org/wiki/Tessa_Jowell'
        form['party_gb_2015'] = self.labour_party_extra.base_id
        form['source'] = "Some source of this information"
        submission_response = form.submit()

        person = Person.objects.get(id='2009')
        party = person.memberships.filter(role='Candidate')

        self.assertEqual(party.count(), 1)
        self.assertEqual(party[0].on_behalf_of.extra.slug, 'party:53')

        links = person.links.all()
        self.assertEqual(links.count(), 1)
        self.assertEqual(links[0].url, 'http://en.wikipedia.org/wiki/Tessa_Jowell')

        # It should redirect back to the same person's page:
        split_location = urlsplit(submission_response.location)
        self.assertEqual(
            '/person/2009',
            split_location.path
        )

    def test_update_dd_mm_yyyy_birth_date(self):
        response = self.app.get(
            '/person/2009/update',
            user=self.user_who_can_lock,
        )
        form = response.forms['person-details']
        form['birth_date'] = '1/4/1875'
        form['source'] = "An update for testing purposes"
        response = form.submit()

        self.assertEqual(response.status_code, 302)
        split_location = urlsplit(response.location)
        self.assertEqual('/person/2009', split_location.path)

        person = Person.objects.get(id='2009')
        self.assertEqual(person.birth_date, '1875-04-01')

    def test_update_person_extra_fields(self):
        ExtraField.objects.create(
            type='url',
            key='cv',
            label='CV or Resumé',
        )
        ExtraField.objects.create(
            type='longer-text',
            key='notes',
            label='Notes',
        )
        response = self.app.get(
            '/person/2009/update',
            user=self.user_who_can_lock,
        )
        form = response.forms['person-details']
        form['birth_date'] = '1/4/1875'
        form['source'] = "An update for testing purposes"
        form['cv'] = 'http://example.org/cv.pdf'
        response = form.submit()

        self.assertEqual(response.status_code, 302)
        split_location = urlsplit(response.location)
        self.assertEqual('/person/2009', split_location.path)

        person = Person.objects.get(id='2009')
        self.assertEqual(person.birth_date, '1875-04-01')
        versions_data = json.loads(person.extra.versions)
        self.assertEqual(
            versions_data[0]['data']['extra_fields'],
            {
                'cv': 'http://example.org/cv.pdf',
                'notes': '',
            }
        )

    def test_update_mark_for_review(self):
        response = self.app.get(
            '/person/2009/update',
            user=self.user_who_can_mark_for_review,
        )
        form = response.forms['person-details']
        form['marked_for_review'] = 'checked'
        form['source'] = "Marked for review due to persistent vandalism"
        response = form.submit()

        self.assertEqual(response.status_code, 302)
        split_location = urlsplit(response.location)
        self.assertEqual('/person/2009', split_location.path)

        person = Person.objects.get(id='2009')
        self.assertEqual(person.extra.marked_for_review, True)

    def test_update_set_mark_for_review_disallowed(self):
        response = self.app.get(
            '/person/2009/update',
            user=self.user,
        )
        form = response.forms['person-details']
        self.assertNotIn('marked_for_review', form.fields)

        # Try adding the field to the form to check someone can't
        # maliciously POST this value and change it.
        add_webtest_form_field(form, Checkbox, 'marked_for_review')

        form['marked_for_review'] = 'checked'
        form['source'] = "Marked for review by a user who shouldn't be allowed to"
        with self.assertRaises(UnauthorizedAttemptToChangeMarkedForReview):
            response = form.submit()

    def test_update_unset_mark_for_review_disallowed(self):
        person_extra = PersonExtra.objects.get(base__pk='2009')
        person_extra.marked_for_review = True
        person_extra.save()
        response = self.app.get(
            '/person/2009/update',
            user=self.user,
        )
        form = response.forms['person-details']
        self.assertNotIn('marked_for_review', form.fields)

        # Try adding the field to the form to check someone can't
        # maliciously POST this value and change it.
        add_webtest_form_field(form, Checkbox, 'marked_for_review')

        form['marked_for_review'] = False
        form['source'] = "Marked for review by a user who shouldn't be allowed to"
        with self.assertRaises(UnauthorizedAttemptToChangeMarkedForReview):
            response = form.submit()
