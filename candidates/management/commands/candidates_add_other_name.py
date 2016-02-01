from __future__ import print_function, unicode_literals

from django.core.management.base import BaseCommand

from popolo.models import Person

from candidates.views.version_data import get_change_metadata


class Command(BaseCommand):

    help = "Add an alternative name to a particular person"

    def add_arguments(self, parser):
        parser.add_argument(
            'PERSON-ID', help='The ID of the person to add a new name for'
        )
        parser.add_argument(
            'OTHER-NAME', help='The new name to add for the person'
        )
        parser.add_argument(
            '--note', help='A note about this alternative name'
        )
        parser.add_argument(
            '--start-date', help='When this other name began being used'
        )
        parser.add_argument(
            '--end-date', help='When this other name stopped being used'
        )
        parser.add_argument(
            '--source', help='The source of information for this other name'
        )

    def handle(self, *args, **options):
        person = Person.objects.get(pk=options['PERSON-ID'])
        kwargs = {
            'name': options['OTHER-NAME'],
        }
        for k in ('note', 'start_date', 'end_date'):
            if options[k]:
                kwargs[k] = options[k]
        person.other_names.create(**kwargs)

        if options['source']:
            source = options['source']
        else:
            source = "Added from the command-line with no source supplied"

        change_metadata = get_change_metadata(None, source)
        person.extra.record_version(change_metadata)
        person.extra.save()

        print("Successfully updated {0}".format(person.name))
