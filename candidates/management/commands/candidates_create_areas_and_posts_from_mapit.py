from __future__ import unicode_literals

from django.core.management.base import BaseCommand, CommandError
from django.utils.translation import ugettext as _
from django.utils.six.moves.urllib_parse import urljoin

from optparse import make_option
import requests

from popolo.models import Post, Area
from candidates.models import PostExtra, AreaExtra
from elections.models import Election, AreaType


"""
This assumes that all the elections in the instance are the same as
far as posts and organization are concerned. It will not work for
instances with different types of election - e.g. Presidential and
parliamentary.
"""
class Command(BaseCommand):
    args = "<MAPIT-URL> <AREA_TYPE> <POST_ID_FORMAT>"
    help = """Create areas and posts based on a mapit area type

MAPIT-URL should be something that returns a set of JSON results
containing areas of type AREA_TYPE. An Area and Post will be created
for each area found using the post and organization information
in the Election objects in the app.
    """

    option_list = BaseCommand.option_list + (
        make_option(
            '--post-label',
            help='Override the format string used to construct the post label [default: "%default"]',
            default=_('{post_role} for {area_name}'),
        ),
    )

    def handle(self, *args, **options):
        post_label_format = _('{post_role} for {area_name}')
        if options['post_label']:
            post_label_format = options['post_label']

        if len(args) != 3:
            raise CommandError("You must provide all three arguments")

        mapit_url, area_type, post_id_format = args

        elections = Election.objects.all()

        if elections.count() == 0:
            raise CommandError("There must be at least one election")

        for election in elections:
            all_areas_url = mapit_url + '/covers' + '?type=' + area_type
            if election.area_generation:
                all_areas_url = all_areas_url + '&generation=' + election.area_generation

            mapit_result = requests.get(all_areas_url)
            mapit_json = mapit_result.json()

            for_post_role = election.for_post_role
            org = election.organization

            if org is None:
                raise CommandError("Election {0} requires an organization".format(election.slug))

            for item in mapit_json.items():
                area_json = item[1]

                area_url = urljoin(mapit_url, '/area/' + str(area_json['id']))

                area, area_created = Area.objects.get_or_create(
                    name=area_json['name'],
                    identifier=area_url,
                    classification=area_json['type_name']
                )

                area_type, created = AreaType.objects.get_or_create(
                    name=area_json['type'],
                    source='MapIt'
                )

                if area_created:
                    area_extra, area_extra_created = AreaExtra.objects.get_or_create(
                        base=area
                    )

                if area_created and area_extra_created:
                    area_extra.type = area_type
                    area_extra.save()

                post_id = post_id_format.format(area_id=area_json['id'])
                post_name = post_label_format.format(
                    area_name=area_json['name'],
                    post_role=for_post_role
                )

                post, created = Post.objects.get_or_create(
                    label=post_name,
                    area=area,
                    organization=org
                )

                post_extra, created = PostExtra.objects.get_or_create(
                    base=post,
                    slug=post_id
                )

                post_extra.elections.add(election)
