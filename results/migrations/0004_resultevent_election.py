# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('results', '0003_resultevent_post_name'),
    ]

    operations = [
        migrations.AddField(
            model_name='resultevent',
            name='election',
            field=models.CharField(max_length=512, null=True, blank=True),
            preserve_default=True,
        ),
    ]
