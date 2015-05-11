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
            name='ResultEvent',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('created', models.DateTimeField(auto_now_add=True)),
                ('winner_popit_person_id', models.CharField(max_length=256)),
                ('winner_person_name', models.CharField(max_length=1024)),
                ('post_id', models.CharField(max_length=256)),
                ('winner_party_id', models.CharField(max_length=256, null=True, blank=True)),
                ('source', models.CharField(max_length=512)),
                ('proxy_image_url_template', models.CharField(max_length=1024, null=True, blank=True)),
                ('user', models.ForeignKey(blank=True, to=settings.AUTH_USER_MODEL, null=True)),
            ],
            options={
                'ordering': ['created'],
            },
            bases=(models.Model,),
        ),
    ]
