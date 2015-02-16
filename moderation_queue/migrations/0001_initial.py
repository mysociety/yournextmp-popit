# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
from django.conf import settings


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='QueuedImage',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('copyright_assigned', models.BooleanField(default=False)),
                ('decision', models.CharField(default=b'undecided', max_length=32, choices=[(b'approved', b'Approved'), (b'rejected', b'Rejected'), (b'undecided', b'Undecided')])),
                ('justification_for_use', models.TextField()),
                ('image', models.ImageField(max_length=512, upload_to=b'queued-images/%Y/%m/%d')),
                ('popit_person_id', models.CharField(max_length=256)),
                ('user', models.ForeignKey(blank=True, to=settings.AUTH_USER_MODEL, null=True)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
    ]
