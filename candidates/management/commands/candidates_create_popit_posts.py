from optparse import make_option

from django.core.management.base import BaseCommand
from django.conf import settings
from django.utils.translation import ugettext as _

from candidates.models.popit import create_or_update
from candidates.popit import PopItApiMixin
from candidates.election_specific import MAPIT_DATA, AREA_POST_DATA

from slumber.exceptions import HttpServerError, HttpClientError

class Command(PopItApiMixin, BaseCommand):
    help = "Create or update the required posts in PopIt"

    option_list = BaseCommand.option_list + (
        make_option(
            '--post-label',
            help='Override the format string used to construct the post label [default: "%default"]',
            default=_('{post_role} for {area_name}'),
        ),
    )

    def handle_mapit_type(self, election, election_data, mapit_type, **options):
        post_label_format = _('{post_role} for {area_name}')
        if options['post_label']:
            post_label_format = options['post_label']
        mapit_tuple = (mapit_type, election_data['mapit_generation'])
        for id, area in MAPIT_DATA.areas_by_id[mapit_tuple].items():
            post_id = AREA_POST_DATA.get_post_id(
                election, mapit_type, id
            )
            role = election_data['for_post_role']
            area_mapit_url = settings.MAPIT_BASE_URL + 'area/' + str(area['id'])
            post_data = {
                'role': role,
                'id': post_id,
                'label': post_label_format.format(
                    post_role=role, area_name=area['name']
                ),
                'area': {
                    'name': area['name'],
                    'id': 'mapit:' + str(area['id']),
                    'identifier': area_mapit_url,
                },
                'organization_id': election_data['organization_id'],
            }
            create_or_update(self.api.posts, post_data)

    def handle(self, **options):
        try:
            for election, election_data in settings.ELECTIONS.items():
                for mapit_type in election_data['mapit_types']:
                    self.handle_mapit_type(
                        election, election_data, mapit_type, **options
                    )
        except (HttpServerError, HttpClientError) as hse:
            print "The body of the error was:", hse.content
            raise
