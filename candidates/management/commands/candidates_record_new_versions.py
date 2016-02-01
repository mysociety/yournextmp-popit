from __future__ import print_function, unicode_literals

from datetime import datetime
from random import randint
import sys

from django.core.management.base import BaseCommand
from django.db import transaction

from candidates.models import PersonExtra


class Command(BaseCommand):

    help = "Record the current version for all people"

    def add_arguments(self, parser):
        parser.add_argument(
            '--person-id',
            help='Only record the current version for the person with this ID'
        )
        parser.add_argument(
            '--source', help='The source of information for this other name'
        )

    def handle(self, *args, **options):
        kwargs = {}
        if options['person_id']:
            kwargs['base__id'] = options['person_id']
        if options['source']:
            source = options['source']
        else:
            source = 'New version recorded from the command-line'
        with transaction.atomic():
            for person_extra in PersonExtra.objects.filter(**kwargs):
                print("Recording the current version of {name} ({id})".format(
                    name=person_extra.base.name, id=person_extra.base.id
                ).encode('utf-8'))
                person_extra.record_version(
                    {
                        'information_source': source,
                        'version_id': "{0:016x}".format(randint(0, sys.maxsize)),
                        'timestamp': datetime.utcnow().isoformat(),
                    }
                )
                person_extra.save()
