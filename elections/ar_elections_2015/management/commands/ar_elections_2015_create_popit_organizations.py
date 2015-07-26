from django.conf import settings
from django.core.management.base import BaseCommand

from candidates.election_specific import PARTY_DATA
from candidates.models.popit import create_or_update
from candidates.popit import PopItApiMixin

class Command(PopItApiMixin, BaseCommand):
    help = "Create the parties for the 2015 elections in Argentina"

    def handle(self, **options):

        # First create all the political parties:

        for party_data in PARTY_DATA.all_party_data:
            create_or_update(
                self.api.organizations,
                party_data,
            )

        # Now we create the organizations that all the posts are
        # associated with:

        for election, election_data in settings.ELECTIONS.items():
            create_or_update(
                self.api.organizations,
                {
                    'id': election_data['organization_id'],
                    'name': election_data['organization_name'],
                }
            )
