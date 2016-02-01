from __future__ import print_function, unicode_literals

from datetime import date

from django.conf import settings
from django.core.management.base import BaseCommand
from django.utils.six.moves.urllib_parse import urljoin

import requests

from candidates.models import AreaExtra, OrganizationExtra, PartySet, PostExtra
from elections.models import AreaType, Election
from popolo.models import Area, Organization, Post

class Command(BaseCommand):

    help = 'Create posts and elections for the 2016 Scottish Parliament elections'

    def handle(self, **options):

        mapit_url = settings.MAPIT_BASE_URL

        gb_parties, _ = PartySet.objects.get_or_create(
            slug='gb', defaults={'name': 'Great Britain'}
        )
        ni_parties, _ = PartySet.objects.get_or_create(
            slug='ni', defaults={'name': 'Northern Ireland'}
        )

        elections = {
            'gb-sp-2016-05-05-r': {
                'name': '2016 Scottish Parliament Election (Regions)',
                'for_post_role': 'Member of the Scottish Parliament',
                'label_format': 'Member of the Scottish Parliament for {area_name}',
                'area_generation': 22,
                'election_date': date(2016, 5, 5),
                'party_lists_in_use': True,
                'mapit_code': 'SPE',
                'area_type_description': 'Scottish Parliament region',
                'organization_slug': 'scottish-parliament',
                'organization_name': 'Scottish Parliament',
            },
            'gb-sp-2016-05-05-c': {
                'name': '2016 Scottish Parliament Election (Constituencies)',
                'for_post_role': 'Member of the Scottish Parliament',
                'label_format': 'Member of the Scottish Parliament for {area_name}',
                'area_generation': 22,
                'election_date': date(2016, 5, 5),
                'party_lists_in_use': False,
                'mapit_code': 'SPC',
                'area_type_description': 'Scottish Parliament constituency',
                'organization_slug': 'scottish-parliament',
                'organization_name': 'Scottish Parliament',
            },
            'gb-naw-2016-05-05-r': {
                'name': '2016 Welsh Assembly Election (Regions)',
                'for_post_role': 'Member of the National Assembly for Wales',
                'label_format': 'Assembly Member for {area_name}',
                'area_generation': 22,
                'election_date': date(2016, 5, 5),
                'party_lists_in_use': True,
                'mapit_code': 'WAE',
                'area_type_description': 'Welsh Assembly region',
                'organization_slug': 'welsh-assembly',
                'organization_name': 'National Assembly for Wales',
            },
            'gb-naw-2016-05-05-c': {
                'name': '2016 Welsh Assembly Election (Constituencies)',
                'for_post_role': 'Member of the National Assembly for Wales',
                'label_format': 'Assembly Member for {area_name}',
                'area_generation': 22,
                'election_date': date(2016, 5, 5),
                'party_lists_in_use': False,
                'mapit_code': 'WAC',
                'area_type_description': 'Welsh Assembly constituency',
                'organization_slug': 'welsh-assembly',
                'organization_name': 'National Assembly for Wales',
            },
            'gb-nia-2016-05-05': {
                'name': '2016 Northern Ireland Assembly Election',
                'for_post_role': 'Member of the Legislative Assembly',
                'label_format': 'Member of the Legislative Assembly for {area_name}',
                'area_generation': 22,
                'election_date': date(2016, 5, 5),
                'party_lists_in_use': False,
                'mapit_code': 'NIE',
                'area_type_description': 'Northern Ireland Assembly constituency',
                'organization_slug': 'northern-ireland-assembly',
                'organization_name': 'Northern Ireland Assembly',
            },
            'gb-gla-2016-05-05-c': {
                'name': '2016 London Assembly Election (Constituencies)',
                'for_post_role': 'Member of the London Assembly',
                'label_format': 'Assembly Member for {area_name}',
                'area_generation': 22,
                'election_date': date(2016, 5, 5),
                'party_lists_in_use': False,
                'mapit_code': 'LAC',
                'area_type_description': 'London Assembly constituency',
                'organization_slug': 'london-assembly',
                'organization_name': 'London Assembly',
            },
            'gb-gla-2016-05-05-a': {
                'name': '2016 London Assembly Election (Additional)',
                'for_post_role': 'Member of the London Assembly',
                'label_format': 'Assembly Member',
                'area_generation': 22,
                'election_date': date(2016, 5, 5),
                'party_lists_in_use': False,
                'mapit_code': 'GLA',
                'area_type_description': 'London Assembly constituency',
                'organization_slug': 'london-assembly',
                'organization_name': 'London Assembly',
            },
        }

        for election_slug, data in elections.items():
            # Make sure the parliament Organization and
            # OrganizationExtra objects exist:
            try:
                organization_extra = OrganizationExtra.objects.get(
                    slug=data['organization_slug']
                )
                organization = organization_extra.base
            except OrganizationExtra.DoesNotExist:
                organization = Organization.objects.create(
                    name=data['organization_name']
                )
                organization_extra = OrganizationExtra.objects.create(
                    base=organization,
                    slug=data['organization_slug']
                )
            # Make sure the Election object exists:
            election_defaults = {
                k: data[k] for k in
                [
                    'name', 'for_post_role', 'area_generation', 'election_date',
                    'party_lists_in_use',
                ]
            }
            election_defaults['current'] = True
            election_defaults['candidate_membership_role'] = 'Candidate'
            print('Creating:', election_defaults['name'], '...',)
            election, created = Election.objects.update_or_create(
                slug=election_slug,
                defaults=election_defaults
            )
            if created:
                print('[created]')
            else:
                print('[already existed]')

            area_type, _ = AreaType.objects.update_or_create(
                name=data['mapit_code'], defaults={'source': 'MapIt'}
            )
            if not election.area_types.filter(name=area_type.name).exists():
                election.area_types.add(area_type)
            url_path = '/areas/' + data['mapit_code']
            url = urljoin(mapit_url, url_path)
            r = requests.get(url)
            for mapit_area_id, mapit_area_data in r.json().items():

                area, _ = Area.objects.update_or_create(
                    identifier=str(mapit_area_id),
                    defaults={'name': mapit_area_data['name']}
                )
                # Now make sure that the MapIt codes are present as identifiers:
                for scheme, identifier in mapit_area_data['codes'].items():
                    area.other_identifiers.update_or_create(
                        scheme=scheme,
                        defaults={'identifier': identifier},
                    )

                AreaExtra.objects.get_or_create(base=area, type=area_type)
                post, _ = Post.objects.update_or_create(
                    organization=organization,
                    area=area,
                    role='Member of the Scottish Parliament',
                    defaults={
                        'label': data['label_format'].format(
                            area_name=area.name
                        )
                    }
                )
                post_extra, _ = PostExtra.objects.update_or_create(
                    base=post,
                    defaults={
                        'slug': str(mapit_area_id),
                        'party_set': gb_parties,
                    },
                )
                post_extra.elections.add(election)
