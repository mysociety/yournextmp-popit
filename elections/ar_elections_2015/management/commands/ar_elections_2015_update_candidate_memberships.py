from __future__ import print_function, unicode_literals

import json

from django.core.management.base import BaseCommand

from elections.models import Election

class Command(BaseCommand):
    help = "Fix all memberships that represent candidacies"

    def handle(self, **options):
        from slumber.exceptions import HttpServerError, HttpClientError
        from candidates.popit import popit_unwrap_pagination

        for membership in popit_unwrap_pagination(
                self.api.memberships, embed='', per_page=100
        ):
            post_id = membership.get('post_id')
            if not post_id:
                continue
            post = self.api.posts(post_id).get(embed='')['result']
            post_role = post['role']
            # Now find the election that matches this membership and role:
            election_found = False
            for edata in Election.objects.all():
                if edata.for_post_role != post_role:
                    continue
                election_found = True
                membership['election'] = edata.slug
                # Now correct the membership role:
                membership['role'] = edata.candidate_membership_role
                # Some of these memberships have a spurious 'area'
                # attribute, set to: {'area': {'name': ''}} which will
                # cause the PUT to fail, so remove that.
                existing_area = membership.get('area')
                if existing_area is not None:
                    if existing_area == {'name': ''}:
                        del membership['area']
                try:
                    self.api.memberships(membership['id']).put(membership)
                except (HttpServerError, HttpClientError) as e:
                    message = "There was an error when putting to membership: {0}"
                    print(message.format(membership['id']))
                    print(json.dumps(membership, indent=True, sort_keys=True))
                    print("The error was:")
                    print(e.content)
                break
            if not election_found:
                message = "Warning: no election found for membership ID {0}"
                print(message.format(membership['id']))
