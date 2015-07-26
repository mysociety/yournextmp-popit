import json

from slumber.exceptions import HttpServerError, HttpClientError

from django.conf import settings
from django.core.management.base import BaseCommand

from candidates.models.popit import membership_covers_date
from candidates.popit import PopItApiMixin, popit_unwrap_pagination

class Command(PopItApiMixin, BaseCommand):
    help = "Set an election field on all memberships that represent candidacies"

    def handle(self, **options):

        for election, election_data in settings.ELECTIONS.items():
            for membership in popit_unwrap_pagination(
                    self.api.memberships, embed='', per_page=100
            ):
                if membership.get('role', '') != election_data['candidate_membership_role']:
                    continue
                if not membership_covers_date(
                        membership, election_data['election_date']
                ):
                    continue
                if membership.get('election', '') == election:
                    # Then the attribute is already correct, don't
                    # bother setting it.
                    continue
                membership['election'] = election
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
                    print message.format(membership['id'])
                    print json.dumps(membership, indent=True, sort_keys=True)
                    print "The error was:"
                    print e.content
