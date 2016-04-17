# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('candidates', '0027_create_standard_complex_fields'),
    ]

    operations = [
        migrations.AddField(
            model_name='extrafield',
            name='order',
            field=models.IntegerField(default=0, blank=True),
        ),
    ]
