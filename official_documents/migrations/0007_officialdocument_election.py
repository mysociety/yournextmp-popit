# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('official_documents', '0006_rename_mapit_id_to_post_id'),
    ]

    operations = [
        migrations.AddField(
            model_name='officialdocument',
            name='election',
            field=models.CharField(max_length=512, null=True, blank=True),
            preserve_default=True,
        ),
    ]
