# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations


def create_simple_fields(apps, schema_editor):
    SimpleField = apps.get_model('candidates', 'SimplePopoloField')
    db_alias = schema_editor.connection.alias

    SimpleField.objects.using(db_alias).bulk_create([
        SimpleField(
            name='honorific_prefix',
            label='Title / pre-nominal honorific (e.g. Dr, Sir, etc.)',
            required=False,
            info_type_key='text',
            order=1,
        ),
        SimpleField(
            name='name',
            label='Full name',
            required=True,
            info_type_key='text',
            order=2,
        ),
        SimpleField(
            name='honorific_suffix',
            label='Post-nominal letters (e.g. CBE, DSO, etc.)',
            required=False,
            info_type_key='text',
            order=3,
        ),
        SimpleField(
            name='email',
            label='Email',
            required=False,
            info_type_key='email',
            order=4,
        ),
        SimpleField(
            name='gender',
            label=u"Gender (e.g. “male”, “female”), Sir, etc.)",
            required=False,
            info_type_key='text',
            order=5,
        ),
        SimpleField(
            name='birth_date',
            label='Date of birth (a four digit year or a full date)',
            required=False,
            info_type_key='text',
            order=6,
        ),
    ])


class Migration(migrations.Migration):

    dependencies = [
        ('candidates', '0021_simplepopolofield'),
    ]

    operations = [
        migrations.RunPython(create_simple_fields),
    ]
