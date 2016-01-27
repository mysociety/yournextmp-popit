# -*- coding: utf-8 -*-

from __future__ import unicode_literals

import re

from django.utils.six.moves.urllib_parse import urlsplit

from django_webtest import WebTest

from popolo.models import Person

from candidates.models import ExtraField, PersonExtraFieldValue, PersonExtra

from .factories import (
    AreaTypeFactory, PartySetFactory, ElectionFactory,
    ParliamentaryChamberFactory
)

from .auth import TestUserMixin


def get_next_dd(start):
    return [t for t in start.next_siblings if t.name == 'dd'][0]


class ExtraFieldTests(TestUserMixin, WebTest):

    def setUp(self):
        # Standard setup (should be factored out):
        wmc_area_type = AreaTypeFactory.create()
        # commons = ParliamentaryChamberFactory.create()
        # gb_parties = PartySetFactory.create(slug='gb', name='Great Britain')
        ElectionFactory.create(
            slug='2015',
            name='2015 General Election',
            area_types=(wmc_area_type,)
        )
        # And now the extra fields:
        p_field = ExtraField.objects.create(
            key='profession',
            label='Profession',
            type=ExtraField.LINE,
        )
        c_field = ExtraField.objects.create(
            key='cv',
            label='Curriculum Vitae or Resumé',
            type=ExtraField.LINE,
        )
        # Create one person with these fields already present:
        self.person = Person.objects.create(
            name="John the Well-Described"
        )
        PersonExtra.objects.create(base=self.person, versions='[]')
        # Now create values for those fields:
        PersonExtraFieldValue.objects.create(
            field=c_field,
            person=self.person,
            value='http://cv.example.org/john'
        )
        PersonExtraFieldValue.objects.create(
            field=p_field,
            person=self.person,
            value='Tree Surgeon'
        )

    def test_create_form_has_fields(self):
        response = self.app.get(
            '/election/2015/person/create/',
            user=self.user
        )
        self.assertEqual(response.status_code, 200)
        # Look for the extra fields' labels:
        p_label = response.html.find('label', {'for': 'id_profession'})
        c_label = response.html.find('label', {'for': 'id_cv'})
        self.assertIsNotNone(p_label)
        self.assertIsNotNone(c_label)
        p_input = response.html.find('input', {'id': 'id_profession'})
        c_input = response.html.find('input', {'id': 'id_cv'})
        self.assertIsNotNone(p_input)
        self.assertIsNotNone(c_input)

    def test_update_form_is_prefilled(self):
        response = self.app.get(
            '/person/{person_id}/update'.format(person_id=self.person.id),
            user=self.user,
        )
        # Look for the extra fields' labels:
        p_label = response.html.find('label', {'for': 'id_profession'})
        c_label = response.html.find('label', {'for': 'id_cv'})
        self.assertIsNotNone(p_label)
        self.assertIsNotNone(c_label)
        p_input = response.html.find('input', {'id': 'id_profession'})
        c_input = response.html.find('input', {'id': 'id_cv'})
        self.assertIsNotNone(p_input)
        self.assertIsNotNone(c_input)
        self.assertEqual(p_input.get('value'), 'Tree Surgeon')
        self.assertEqual(c_input.get('value'), 'http://cv.example.org/john')

    def test_fields_are_saved_when_editing(self):
        response = self.app.get(
            '/person/{person_id}/update'.format(person_id=self.person.id),
            user=self.user,
        )
        form = response.forms['person-details']
        form['cv'] = 'http://homepage.example.org/john-the-described'
        form['profession'] = 'Soda Jerk'
        form['source'] = 'Testing setting additional fields'
        submission_response = form.submit()

        self.assertEqual(submission_response.status_code, 302)
        split_location = urlsplit(submission_response.location)
        self.assertEqual(
            '/person/{person_id}'.format(person_id=self.person.id),
            split_location.path
        )

        person = Person.objects.get(id=self.person.id)
        self.assertEqual(
            PersonExtraFieldValue.objects.get(
                person=person, field__key='cv'
            ).value,
            'http://homepage.example.org/john-the-described'
        )
        self.assertEqual(
            PersonExtraFieldValue.objects.get(
                person=person, field__key='profession'
            ).value,
            'Soda Jerk'
        )

    def test_fields_are_saved_when_creating(self):
        response = self.app.get(
            '/election/2015/person/create/',
            user=self.user
        )
        form = response.forms['person-details']
        form['name'] = 'Naomi Newperson'
        form['cv'] = 'http://example.org/another-cv'
        form['profession'] = 'Longshoreman'
        form['standing_2015'] = 'not-standing'
        form['source'] = 'Test creating someone with additional fields'
        submission_response = form.submit()

        self.assertEqual(submission_response.status_code, 302)
        split_location = urlsplit(submission_response.location)
        m = re.search(r'^/person/(.*)', split_location.path)
        self.assertTrue(m)

        person = Person.objects.get(id=m.group(1))
        self.assertEqual(
            PersonExtraFieldValue.objects.get(
                person=person, field__key='cv'
            ).value,
            'http://example.org/another-cv'
        )
        self.assertEqual(
            PersonExtraFieldValue.objects.get(
                person=person, field__key='profession'
            ).value,
            'Longshoreman'
        )

    def test_view_additional_fields(self):
        response = self.app.get(
            '/person/{person_id}'.format(person_id=self.person.id)
        )

        cv_dt = response.html.find('dt', text='Curriculum Vitae or Resumé')
        cv_dd = get_next_dd(cv_dt)
        self.assertEqual(cv_dd.text.strip(), 'http://cv.example.org/john')

        profession_dt = response.html.find('dt', text='Profession')
        profession_dd = get_next_dd(profession_dt)
        self.assertEqual(profession_dd.text.strip(), 'Tree Surgeon')
