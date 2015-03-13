import sys

from candidates.popit import PopItApiMixin, popit_unwrap_pagination
from candidates.update import fix_dates

from django.core.management.base import BaseCommand

from slumber.exceptions import HttpClientError


class Command(PopItApiMixin, BaseCommand):

    def handle(self, **options):
        for person in popit_unwrap_pagination(
                self.api.persons,
                per_page=100
        ):
            needs_update = False
            for version in person.get('versions', []):
                data = version['data']
                if data.get('last_party'):
                    needs_update = True
                    msg = "Fixing person {0}persons/{1}"
                    print msg.format(self.get_base_url(), person['id'])
                    del data['last_party']
            if not needs_update:
                continue
            for image in person.get('images', []):
                image.pop('_id', None)
                # Some images have an empty 'created' field, which
                # causes an Elasticsearch indexing error, so remove
                # that if it's the case:
                if not image.get('created'):
                    image.pop('created', None)
            fix_dates(person)
            try:
                self.api.persons(person['id']).put(person)
            except HttpClientError as e:
                print "HttpClientError", e.content
                sys.exit(1)
