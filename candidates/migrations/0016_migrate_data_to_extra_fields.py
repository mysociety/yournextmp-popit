# -*- coding: utf-8 -*-
from __future__ import print_function, unicode_literals

from django.db import models, migrations
from django.conf import settings

def from_person_extra_to_generic_fields(apps, schema_editor):
    ExtraField = apps.get_model('candidates', 'ExtraField')
    PersonExtraFieldValue = apps.get_model('candidates', 'PersonExtraFieldValue')
    PersonExtra = apps.get_model('candidates', 'PersonExtra')
    if settings.ELECTION_APP == 'cr':
        p_field = ExtraField.objects.create(
            key='profession',
            type='line',
            label='Profession',
        )
    elif settings.ELECTION_APP == 'bf_elections_2015':
        c_field = ExtraField.objects.create(
            key='cv',
            type='longer-text',
            label='CV or Résumé',
        )
        p_field = ExtraField.objects.create(
            key='program',
            type='longer-text',
            label='Program',
        )
        for pe in PersonExtra.objects.all():
            person = pe.base
            PersonExtraFieldValue.objects.create(
                person=person,
                field=c_field,
                value=pe.cv
            )
            PersonExtraFieldValue.objects.create(
                person=person,
                field=p_field,
                value=pe.program
            )

def from_generic_fields_to_person_extra(apps, schema_editor):
    ExtraField = apps.get_model('candidates', 'ExtraField')
    PersonExtraFieldValue = apps.get_model('candidates', 'PersonExtraFieldValue')
    if settings.ELECTION_APP == 'bf_elections_2015':
        for pefv in PersonExtraFieldValue.objects.select_related('field'):
            pe = pefv.person.extra
            if pefv.field.key == 'cv':
                pe.cv = pefv.value
                pe.save()
            elif pefv.field.key == 'program':
                pe.program = pefv.value
                pe.save()
            else:
                print("Ignoring field with unknown key:", pefv.field.key)
    PersonExtraFieldValue.objects.all().delete()
    ExtraField.objects.all().delete()


class Migration(migrations.Migration):

    dependencies = [
        ('candidates', '0015_add_configurable_extra_fields'),
    ]

    operations = [
        migrations.RunPython(
            from_person_extra_to_generic_fields,
            from_generic_fields_to_person_extra
        )
    ]
