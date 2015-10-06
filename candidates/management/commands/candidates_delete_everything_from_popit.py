import json

from candidates.models import PopItPerson
from candidates.popit import PopItApiMixin, get_base_url

from django.core.management.base import BaseCommand

class Command(PopItApiMixin, BaseCommand):

    def handle(self, **options):
        message = "WARNING: this will delete all people, posts, " \
            "organizations and\nmemberships from the PopIt instance:" + \
            "\n\n  " + get_base_url() + "\n\nIf you really want to do " + \
            "this, type 'YES':"
        self.stdout.write(message)
        user_response = raw_input()
        if user_response != 'YES':
            self.stdout.write("Aborting, since you didn't type 'YES'.")
            return
        for collection in (
                'memberships',
                'posts',
                'organizations',
                'persons',
        ):
            self.stdout.write("Deleting from collection: " + collection)
            api_collection = getattr(self.api, collection)
            # We have to be careful here - if you try to step to page
            # 2 after deleting everything on page 1, then lots of
            # objects will be missed. Instead, just get the first page
            # until there's nothing left.
            while True:
                results = api_collection.get()
                for o in results['result']:
                    object_id = o['id']
                    api_collection(object_id).delete()
                if not results.get('has_more'):
                    break
