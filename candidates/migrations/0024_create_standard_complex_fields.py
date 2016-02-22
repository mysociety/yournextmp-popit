# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations


def remove_standard_fields(apps, schema_editor):
    ComplexField = apps.get_model('candidates', 'ComplexPopoloField')
    db_alias = schema_editor.connection.alias
    ComplexField.objects.using(db_alias).all().delete()


def create_complex_fields(apps, schema_editor):
    ComplexField = apps.get_model('candidates', 'ComplexPopoloField')
    db_alias = schema_editor.connection.alias

    ComplexField.objects.using(db_alias).bulk_create([
        ComplexField(
            name='twitter_username',
            label='Twitter username (e.g. democlub)',
            field_type='text',
            popolo_array='contact_details',
            info_type_key='contact_type',
            info_type='twitter',
            info_value_key='value',
            order=1,
        ),
        ComplexField(
            name='facebook_personal_url',
            label='Facebook profile URL',
            field_type='url',
            popolo_array='links',
            info_type_key='note',
            info_type='facebook personal',
            info_value_key='url',
            order=2,
        ),
        ComplexField(
            name='facebook_page_url',
            label='Facebook page (e.g. for their campaign)',
            field_type='url',
            popolo_array='links',
            info_type_key='note',
            info_type='facebook page',
            info_value_key='url',
            order=3,
        ),
        ComplexField(
            name='homepage_url',
            label='Homepage URL',
            field_type='url',
            popolo_array='links',
            info_type_key='note',
            info_type='homepage',
            info_value_key='url',
            order=4,
        ),
        ComplexField(
            name='wikipedia_url',
            label='Wikipedia URL',
            field_type='url',
            popolo_array='links',
            info_type_key='note',
            info_type='wikipedia',
            info_value_key='url',
            order=5,
        ),
        ComplexField(
            name='linkedin_url',
            label='LinkedIn URL',
            field_type='url',
            popolo_array='links',
            info_type_key='note',
            info_type='linkedin',
            info_value_key='url',
            order=6,
        ),
        ComplexField(
            name='party_ppc_page_url',
            label="The party's candidate page for this person",
            field_type='url',
            popolo_array='links',
            info_type_key='note',
            info_type='party candidate page',
            old_info_type='party PPC page',
            info_value_key='url',
            order=7,
        ),
    ])


class Migration(migrations.Migration):

    dependencies = [
        ('candidates', '0023_complexpopolofield'),
    ]

    operations = [
        migrations.RunPython(create_complex_fields, remove_standard_fields),
    ]
