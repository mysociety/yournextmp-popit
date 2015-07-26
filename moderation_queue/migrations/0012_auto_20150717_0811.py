# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('moderation_queue', '0011_queuedimage_face_detection_tried'),
    ]

    operations = [
        migrations.AlterField(
            model_name='queuedimage',
            name='created',
            field=models.DateTimeField(auto_now_add=True),
        ),
        migrations.AlterField(
            model_name='queuedimage',
            name='updated',
            field=models.DateTimeField(auto_now=True),
        ),
    ]
