# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations

def change_constituency_to_post(apps, schema_editor):
    CachedCount = apps.get_model('cached_counts', 'CachedCount')
    for cc in CachedCount.objects.all():
        if cc.count_type == 'constituency':
            cc.count_type = 'post'
            cc.save()

class Migration(migrations.Migration):

    dependencies = [
        ('cached_counts', '0003_set_default_election'),
    ]

    operations = [
        migrations.RunPython(change_constituency_to_post),
    ]
