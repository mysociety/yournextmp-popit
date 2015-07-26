# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('official_documents', '0005_auto_20150410_1307'),
    ]

    operations = [
        migrations.RenameField(
            model_name='officialdocument',
            old_name='mapit_id',
            new_name='post_id',
        ),
    ]
