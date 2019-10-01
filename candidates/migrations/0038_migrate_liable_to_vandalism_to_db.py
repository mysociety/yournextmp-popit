# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.conf import settings
from django.db import migrations


def migrate_liable_to_vandalism_from_settings_to_db(apps, schema_editor):
    PersonExtra = apps.get_model('candidates', 'PersonExtra')
    PersonExtra.objects.filter(pk__in=settings.PEOPLE_LIABLE_TO_VANDALISM) \
        .update(marked_for_review=True)


class Migration(migrations.Migration):

    dependencies = [
        ('candidates', '0037_personextra_marked_for_review'),
    ]

    operations = [
        migrations.RunPython(
            migrate_liable_to_vandalism_from_settings_to_db,
            lambda apps, schema_editor: None
        )
    ]
