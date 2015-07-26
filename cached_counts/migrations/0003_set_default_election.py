# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations

# This migration should only need to run by original YourNextMP
# installations, for the UK 2015 General Election; any future
# installations will set the right election when creating CachedCount
# objects.

def set_uk_2015_election(apps, schema_editor):
    CachedCount = apps.get_model('cached_counts', 'CachedCount')
    for cc in CachedCount.objects.all():
        if not cc.election:
            cc.election = '2015'
            cc.save()


class Migration(migrations.Migration):

    dependencies = [
        ('cached_counts', '0002_cachedcount_election'),
    ]

    operations = [
        migrations.RunPython(
            set_uk_2015_election,
            lambda apps, schema_editor: None
        ),
    ]
