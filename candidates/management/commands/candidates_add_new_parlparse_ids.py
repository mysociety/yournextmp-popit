from __future__ import unicode_literals

import requests

from django.core.management.base import BaseCommand, CommandError

from candidates.views.version_data import get_change_metadata

class Command(BaseCommand):
    args = "<person.js URL>"
    help = "Find any new parlparse IDs from parlparse and add them"

    def handle(self, *args, **options):
        from candidates.models import PopItPerson
        from candidates.popit import create_popit_api_object

        self.verbosity = int(options.get('verbosity', 1))
        api = create_popit_api_object()
        if len(args) != 1:
            raise CommandError("You must provide a person.js URL")
        person_js_url = args[0]
        people_data = requests.get(person_js_url).json()
        for person_data in people_data['persons']:
            twfy_person = PopItPerson.create_from_dict(person_data)
            ynmp_id = twfy_person.get_identifier('yournextmp')
            if not ynmp_id:
                continue
            parlparse_id = twfy_person.id
            ynmp_person = PopItPerson.create_from_popit(api, ynmp_id)
            existing_parlparse_id = ynmp_person.get_identifier('uk.org.publicwhip')
            if existing_parlparse_id:
                if existing_parlparse_id == parlparse_id:
                    # That's fine, there's already the right parlparse ID
                    pass
                else:
                    # Otherwise there's a mismatch, which needs investigation
                    msg = "Warning: parlparse ID mismatch between YNMP {0} "
                    msg += "and TWFY {1} for YNMP person {2}\n"
                    self.stderr.write(
                        msg.format(
                            existing_parlparse_id,
                            parlparse_id,
                            ynmp_id,
                        )
                    )
                continue
            msg = "Updating the YourNextMP person {0} with parlparse_id {1}\n"
            self.stdout.write(msg.format(ynmp_id, parlparse_id))
            ynmp_person.set_identifier(
                'uk.org.publicwhip',
                parlparse_id,
            )
            change_metadata = get_change_metadata(
                None, "Fetched a new parlparse ID"
            )
            ynmp_person.record_version(change_metadata)
            ynmp_person.save_to_popit(api)
            ynmp_person.invalidate_cache_entries()
