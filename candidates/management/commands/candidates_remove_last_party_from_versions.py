from candidates.models import PopItPerson
from candidates.popit import (
    PopItApiMixin, popit_unwrap_pagination, get_base_url
)

from django.core.management.base import BaseCommand


class Command(PopItApiMixin, BaseCommand):

    def handle(self, **options):
        for person_data in popit_unwrap_pagination(
                self.api.persons,
                embed='',
                per_page=100
        ):
            needs_update = False
            for version in person_data.get('versions', []):
                data = version['data']
                if data.get('last_party'):
                    needs_update = True
                    msg = "Fixing person {0}persons/{1}"
                    print msg.format(get_base_url(), person_data['id'])
                    del data['last_party']
            if not needs_update:
                continue
            person = PopItPerson.create_from_dict(person_data)
            person.save_to_popit(self.api)
            person.invalidate_cache_entries()
