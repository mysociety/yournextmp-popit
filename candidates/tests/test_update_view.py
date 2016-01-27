# -*- coding: utf-8 -*-

from __future__ import unicode_literals

import json

from django.utils.six.moves.urllib_parse import urlsplit

from django_webtest import WebTest

from .auth import TestUserMixin

from popolo.models import Person

from candidates.models import ExtraField
from .factories import (
    AreaTypeFactory, ElectionFactory, CandidacyExtraFactory,
    ParliamentaryChamberFactory, PartyFactory, PartyExtraFactory,
    PersonExtraFactory, PostExtraFactory, PartySetFactory
)


class TestUpdatePersonView(TestUserMixin, WebTest):

    def setUp(self):
        wmc_area_type = AreaTypeFactory.create()
        gb_parties = PartySetFactory.create(slug='gb', name='Great Britain')
        self.election = ElectionFactory.create(
            slug='2015',
            name='2015 General Election',
            area_types=(wmc_area_type,)
        )
        commons = ParliamentaryChamberFactory.create()
        self.post_extra = PostExtraFactory.create(
            elections=(self.election,),
            base__organization=commons,
            slug='65808',
            base__label='Member of Parliament for Dulwich and West Norwood',
            party_set=gb_parties,
        )
        PartyExtraFactory.reset_sequence()
        PartyFactory.reset_sequence()
        self.parties = {}
        for i in range(0, 4):
            party_extra = PartyExtraFactory.create()
            gb_parties.parties.add(party_extra.base)
            self.parties[party_extra.slug] = party_extra
        person_extra = PersonExtraFactory.create(
            base__id='2009',
            base__name='Tessa Jowell'
        )

        CandidacyExtraFactory.create(
            election=self.election,
            base__person=person_extra.base,
            base__post=self.post_extra.base,
            base__on_behalf_of=self.parties['party:63'].base
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
        form['party_gb_2015'] = self.parties['party:53'].base_id
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
        form['party_gb_2015'] = self.parties['party:53'].base_id
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
