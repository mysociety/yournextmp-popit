# This dumps data from the live YourNextMP PopIt database into a
# format that can be used to replace the data in a local PopIt
# instance PopIt instance.  We recommend that you do this with PopIt's
# replace-database script, but you could also manually mongoimport
# these files.

import json

from popit_api import PopIt

from django.core.management.base import BaseCommand

from ...popit import popit_unwrap_pagination

class Command(BaseCommand):

    def handle(self, **options):
        api = PopIt(
            instance='yournextmp',
            hostname='popit.mysociety.org',
            api_version='v0.1',
            append_slash=False,
        )
        for collection in ('persons', 'organizations', 'posts', 'memberships'):
            print "Downloading {0}...".format(collection)
            filename = 'yournextrepresentative-{0}.dump'.format(collection)
            with open(filename, 'w') as f:
                for o in popit_unwrap_pagination(
                        getattr(api, collection),
                        per_page=100
                ):
                    o.pop('memberships', None)
                    o['_id'] = o['id']
                    f.write(json.dumps(o, sort_keys=True))
                    f.write("\n")
