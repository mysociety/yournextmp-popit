# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('candidates', '0020_cr_add_reelection_field'),
    ]

    operations = [
        migrations.CreateModel(
            name='SimplePopoloField',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(max_length=256, choices=[(b'name', 'Name'), (b'family_name', 'Family Name'), (b'given_name', 'Given Name'), (b'additional_name', 'Additional Name'), (b'honorific_prefix', 'Honorific Prefix'), (b'honorific_suffix', 'Honorific Suffix'), (b'patronymic_name', 'Patronymic Name'), (b'sort_name', 'Sort Name'), (b'email', 'Email'), (b'gender', 'Gender'), (b'birth_date', 'Birth Date'), (b'death_date', 'Death Date'), (b'summary', 'Summary'), (b'biography', 'Biography'), (b'national_identity', 'National Identity')])),
                ('label', models.CharField(max_length=256)),
                ('required', models.BooleanField(default=False)),
                ('info_type_key', models.CharField(max_length=256, choices=[(b'text', 'Text Field'), (b'email', 'Email Field')])),
                ('order', models.IntegerField(blank=True)),
            ],
        ),
    ]
