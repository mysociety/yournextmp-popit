from __future__ import print_function, unicode_literals

from django.core.management.base import BaseCommand

from popolo.models import Person

from candidates.views.version_data import get_change_metadata

class Command(BaseCommand):

    help = "Add an identifier to a particular person"

    def add_arguments(self, parser):
        parser.add_argument(
            'PERSON-ID',
            help='The ID of the person to add a new identifer for'
        )
        parser.add_argument(
            'SCHEME',
            help='The scheme of the new identifier'
        )
        parser.add_argument(
            'IDENTIFIER',
            help='The identifier to add'
        )
        parser.add_argument(
            '--source', help='The source of information for this new identifier'
        )

    def handle(self, *args, **options):
        person = Person.objects.get(pk=options['PERSON-ID'])
        person.identifiers.create(
            scheme=options['SCHEME'],
            identifier=options['IDENTIFIER'],
        )

        if options['source']:
            source = options['source']
        else:
            source = "Added from the command-line with no source supplied"

        change_metadata = get_change_metadata(None, source)
        person.extra.record_version(change_metadata)
        person.extra.save()

        print("Successfully updated {0}".format(person.name))
