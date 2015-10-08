# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('cached_counts', '0004_constituency_to_post'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='cachedcount',
            options={'ordering': ['-election_dateA', '-count', 'name']},
        ),
        migrations.AddField(
            model_name='cachedcount',
            name='election_dateA',
            field=models.DateField(null=True, blank=True),
        ),
    ]
