# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('candidates', '0036_add_trusted_to_mark_for_review_group'),
    ]

    operations = [
        migrations.AddField(
            model_name='personextra',
            name='marked_for_review',
            field=models.BooleanField(default=False),
        ),
    ]
