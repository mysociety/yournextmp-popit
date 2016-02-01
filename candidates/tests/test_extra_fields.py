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

        yn_field = ExtraField.objects.create(
            key='reelection',
            label=u'Standing for re-election',
            type=ExtraField.YESNO
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
        PersonExtraFieldValue.objects.create(
            field=yn_field,
            person=self.person,
            value='yes'
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
        yn_label = response.html.find('label', {'for': 'id_reelection'})
        self.assertIsNotNone(p_label)
        self.assertIsNotNone(c_label)
        self.assertIsNotNone(yn_label)
        p_input = response.html.find('input', {'id': 'id_profession'})
        c_input = response.html.find('input', {'id': 'id_cv'})
        yn_input = response.html.find('select', {'id': 'id_reelection'})
        self.assertIsNotNone(p_input)
        self.assertIsNotNone(c_input)
        self.assertIsNotNone(yn_input)

    def test_update_form_is_prefilled(self):
        response = self.app.get(
            '/person/{person_id}/update'.format(person_id=self.person.id),
            user=self.user,
        )
        # Look for the extra fields' labels:
        p_label = response.html.find('label', {'for': 'id_profession'})
        c_label = response.html.find('label', {'for': 'id_cv'})
        yn_label = response.html.find('label', {'for': 'id_reelection'})
        self.assertIsNotNone(p_label)
        self.assertIsNotNone(c_label)
        self.assertIsNotNone(yn_label)
        p_input = response.html.find('input', {'id': 'id_profession'})
        c_input = response.html.find('input', {'id': 'id_cv'})
        yn_input = response.html.find('select', {'id': 'id_reelection'})
        self.assertIsNotNone(p_input)
        self.assertIsNotNone(c_input)
        self.assertIsNotNone(yn_input)
        self.assertEqual(p_input.get('value'), 'Tree Surgeon')
        self.assertEqual(c_input.get('value'), 'http://cv.example.org/john')
        form = response.forms['person-details']
        self.assertEqual(form['reelection'].value, 'yes')

    def test_fields_are_saved_when_editing(self):
        response = self.app.get(
            '/person/{person_id}/update'.format(person_id=self.person.id),
            user=self.user,
        )
        form = response.forms['person-details']
        form['cv'] = 'http://homepage.example.org/john-the-described'
        form['profession'] = 'Soda Jerk'
        form['reelection'] = 'no'
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
        self.assertEqual(
            PersonExtraFieldValue.objects.get(
                person=person, field__key='reelection'
            ).value,
            'no'
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
        form['reelection'] = 'yes'
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
        self.assertEqual(
            PersonExtraFieldValue.objects.get(
                person=person, field__key='reelection'
            ).value,
            'yes'
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

        profession_dt = response.html.find('dt', text=u'Standing for re-election')
        profession_dd = get_next_dd(profession_dt)
        self.assertEqual(profession_dd.text.strip(), 'Yes')
