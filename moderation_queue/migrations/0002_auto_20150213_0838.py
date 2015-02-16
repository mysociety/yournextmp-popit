# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import datetime


class Migration(migrations.Migration):

    dependencies = [
        ('moderation_queue', '0001_initial'),
    ]

    operations = [
        migrations.RenameField(
            model_name='queuedimage',
            old_name='copyright_assigned',
            new_name='use_allowed_by_owner',
        ),
        migrations.AddField(
            model_name='queuedimage',
            name='created',
            field=models.DateTimeField(default=datetime.datetime.now, auto_now_add=True),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='queuedimage',
            name='public_domain',
            field=models.BooleanField(default=False),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='queuedimage',
            name='updated',
            field=models.DateTimeField(default=datetime.datetime.now, auto_now=True),
            preserve_default=True,
        ),
    ]
