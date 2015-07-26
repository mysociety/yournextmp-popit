import sys

from candidates.models import PopItPerson
from candidates.popit import (
    PopItApiMixin, popit_unwrap_pagination, get_base_url
)

from django.core.management.base import BaseCommand

from slumber.exceptions import HttpClientError


def strip_bogus_fields(data, bogus_field_keys):
    for key in bogus_field_keys:
        if key in data:
            print "Stripping out", key
            del data[key]


class Command(PopItApiMixin, BaseCommand):

    def handle(self, **options):
        for person_data in popit_unwrap_pagination(
                self.api.persons,
                embed='',
                per_page=100
        ):
            msg = "Person {0}persons/{1}"
            print msg.format(get_base_url(), person_data['id'])
            strip_bogus_fields(
                person_data,
                [
                    'founding_date',
                    'dissolution_date',
                    'start_date',
                    'end_date'
                ]
            )
            for image in person_data.get('images', []):
                strip_bogus_fields(
                    image,
                    [
                        'birth_date',
                        'death_date',
                        'founding_date',
                        'dissolution_date',
                        'start_date',
                        'end_date'
                    ]
                )
            person = PopItPerson.create_from_dict(person_data)
            person.save_to_popit(self.api)
            person.invalidate_cache_entries()
