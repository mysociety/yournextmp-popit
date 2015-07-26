# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations

# This migration should only need to run by original YourNextMP
# installations, for the UK 2015 General Election; any future
# installations will set the right election when creating official
# documents.

def set_uk_2015_election(apps, schema_editor):
    OfficialDocument = apps.get_model('official_documents', 'OfficialDocument')
    for od in OfficialDocument.objects.all():
        if not od.election:
            od.election = '2015'
            od.save()

class Migration(migrations.Migration):

    dependencies = [
        ('official_documents', '0007_officialdocument_election'),
    ]

    operations = [
        migrations.RunPython(
            set_uk_2015_election,
            lambda apps, schema_editor: None,
        )
    ]
