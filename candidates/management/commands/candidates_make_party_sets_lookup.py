import json
from os.path import dirname, join, realpath

from django.conf import settings
from django.core.management.base import BaseCommand

from candidates.election_specific import AREA_POST_DATA
from candidates.popit import get_all_posts

class Command(BaseCommand):

    def handle(self, **options):
        repo_root = realpath(join(dirname(__file__), '..', '..', '..'))
        output_filename = join(
            repo_root,
            'elections',
            settings.ELECTION_APP,
            'static',
            'js',
            'post-to-party-set.js',
        )
        with open(output_filename, 'w') as f:
            f.write('var postIDToPartySet = ')
            mapping = {
                post['id']: AREA_POST_DATA.post_id_to_party_set(post['id'])
                for election, election_data in settings.ELECTIONS_CURRENT
                for post in get_all_posts(election_data['for_post_role'])
            }
            unknown_post_ids = [
                k for k, v in mapping.items()
                if v is None
            ]
            f.write(json.dumps(mapping))
            f.write(';\n')
            if unknown_post_ids:
                print "Warning: no party set could be found for these post IDs:"
                print unknown_post_ids
