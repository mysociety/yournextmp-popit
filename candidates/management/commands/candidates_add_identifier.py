from django.core.management.base import BaseCommand, CommandError

from candidates.models import PopItPerson
from candidates.popit import create_popit_api_object

class Command(BaseCommand):
    args = "<PERSON-ID> <SCHEME> <IDENTIFIER>"
    help = "Add an identifier to a particular person"

    def handle(self, *args, **options):
        self.verbosity = int(options.get('verbosity', 1))
        api = create_popit_api_object()
        if len(args) != 3:
            raise CommandError("You must provide all three arguments")

        person_id, scheme, identifier = args

        person = PopItPerson.create_from_popit(api, person_id)

        person.identifiers.append(
            {
                'scheme': scheme,
                'identifier': identifier,
            }
        )

        person.save_to_popit(api)
        person.invalidate_cache_entries()

        # FIXME: this should create a new version in the versions
        # array too, otherwise you manually have to edit on YourNextMP
        # too to create a new version with a change message.

        print "Successfully updated {0}".format(person_id)
