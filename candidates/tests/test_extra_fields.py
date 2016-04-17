# -*- coding: utf-8 -*-

from __future__ import unicode_literals

import re

from django.utils.six.moves.urllib_parse import urlsplit

from django_webtest import WebTest

from popolo.models import Person

from candidates.models import ExtraField, PersonExtraFieldValue, PersonExtra

from .auth import TestUserMixin
from .uk_examples import UK2015ExamplesMixin


class ExtraFieldTests(TestUserMixin, UK2015ExamplesMixin, WebTest):

    def setUp(self):
        super(ExtraFieldTests, self).setUp()
        # Create the extra fields:
        p_field = ExtraField.objects.create(
            key='profession',
            label='Profession',
            type=ExtraField.LINE,
            order=3
        )
        c_field = ExtraField.objects.create(
            key='cv',
            label='Curriculum Vitae or Resumé',
            type=ExtraField.LINE,
            order=1
        )

        yn_field = ExtraField.objects.create(
            key='reelection',
            label='Standing for re-election',
            type=ExtraField.YESNO,
            order=2
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
        form = response.forms['new-candidate-form']
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
        cv_dd = cv_dt.find_next_sibling('dd')
        self.assertEqual(cv_dd.text.strip(), 'http://cv.example.org/john')

        reelection_dt = cv_dt.find_next_sibling('dt')
        reelection_dd = reelection_dt.find_next_sibling('dd')
        self.assertEqual(reelection_dt.text.strip(), 'Standing for re-election')
        self.assertEqual(reelection_dd.text.strip(), 'Yes')

        profession_dt = reelection_dt.find_next_sibling('dt')
        profession_dd = profession_dt.find_next_sibling('dd')
        self.assertEqual(profession_dt.text.strip(), 'Profession')
        self.assertEqual(profession_dd.text.strip(), 'Tree Surgeon')
