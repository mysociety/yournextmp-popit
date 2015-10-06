import requests

import time

from candidates.popit import (
    PopItApiMixin, popit_unwrap_pagination, get_base_url, get_search_url
)

from django.core.management.base import BaseCommand

class Command(PopItApiMixin, BaseCommand):

    def handle(self, **options):

        collections = ('membership',)

        for collection in collections:
            plural = collection + 's'
            api_collection = getattr(self.api, plural)

            for item in popit_unwrap_pagination(
                    api_collection,
                    per_page=100
            ):
                item_id = item['id']
                search_url = get_search_url(
                    plural, 'id:{0}'.format(item_id)
                )
                r = requests.get(search_url)
                time.sleep(1)
                items_found = r.json()['total']
                if items_found != 1:
                    message = (
                        "Found {total} people with ID {item_id} " +
                        "{base_url}items/{item_id} - search URL was: " +
                        "{search_url}"
                    )
                    print message.format(
                        total=items_found,
                        item_id=item_id,
                        base_url=get_base_url(),
                        search_url=search_url,
                    )
