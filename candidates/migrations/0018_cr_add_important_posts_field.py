# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.conf import settings
from django.db import models, migrations

def add_extra_field(apps, schema_editor):
    ExtraField = apps.get_model('candidates', 'ExtraField')
    if settings.ELECTION_APP == 'cr':
         ExtraField.objects.create(
            key='important_roles',
            type='longer-text',
            label='Important Roles',
        )

def remove_extra_field(apps, schema_editor):
    ExtraField = apps.get_model('candidates', 'ExtraField')
    if settings.ELECTION_APP == 'cr':
        extra_field = ExtraField.objects.get('important_roles')
        extra_field.personextrafieldvalue_set.all().delete()
        extra_field.delete()


class Migration(migrations.Migration):

    dependencies = [
        ('candidates', '0017_remove_cv_and_program_fields'),
    ]

    operations = [
        migrations.RunPython(add_extra_field, remove_extra_field)
    ]
