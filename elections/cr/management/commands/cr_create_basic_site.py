# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from datetime import date

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils.text import slugify

from candidates.models import (
    AreaExtra, OrganizationExtra, PostExtra, PartySet
)
from elections.models import AreaType, Election
from popolo.models import Area, Organization, Post
import requests

class Command(BaseCommand):

    def get_or_create_organization(self, slug, name):
        try:
            org_extra = OrganizationExtra.objects.get(slug=slug)
            org = org_extra.base
            org.name = name
            org.save()
        except OrganizationExtra.DoesNotExist:
            org = Organization.objects.create(name=name)
            org_extra = OrganizationExtra.objects.create(base=org, slug=slug)
        return org

    def handle(self, *args, **options):
        with transaction.atomic():
            # Create all the AreaType objects first:
            area_type, created = AreaType.objects.get_or_create(
                name='CRCANTON',
                defaults={'source': 'MapIt'},
            )
            # Now the Election objects (and the organizations they're
            # associated with)
            elections = []
            for election_data in [
                    {
                        'slug': 'mun-al-2016',
                        'for_post_role': 'Alcalde',
                        'name': 'Elección de Alcaldes 2016',
                        'organization_name': 'Alcaldía Municipal',
                        'organization_slug': 'alcaldia-municipal',
                        'party_lists_in_use': False,
                    },
                    {
                        'slug': 'mun-re-2016',
                        'for_post_role': 'Regidor',
                        'name': 'Elección de Regidores 2016',
                        'organization_name': 'Consejo Municipal',
                        'organization_slug': 'consejo-municipal',
                        'party_lists_in_use': True,
                        'default_party_list_members_to_show': 3,
                    },
            ]:
                org = self.get_or_create_organization(
                    election_data['organization_slug'],
                    election_data['organization_name'],
                )
                del election_data['organization_name']
                del election_data['organization_slug']
                election_data['organization'] = org
                consistent_data = {
                    'candidate_membership_role': 'Candidate',
                    'election_date': date(2016, 2, 7),
                    'current': True,
                    'use_for_candidate_suggestions': False,
                    'area_generation': 2,
                    'organization': org,
                }
                election_slug = election_data.pop('slug')
                election_data.update(consistent_data)
                election, created = Election.objects.update_or_create(
                    slug=election_slug,
                    defaults=election_data,
                )
                election.area_types.add(area_type)
                elections.append(election)
            # Now create all the Area objects:
            areas = []
            for area_id, area_data in requests.get(
                    'http://international.mapit.mysociety.org/areas/CRCANTON'
            ).json().items():
                area, created = Area.objects.update_or_create(
                    identifier=area_data['id'],
                    defaults={
                        'name': area_data['name'],
                        'classification': area_data['type_name'],
                    }
                )
                AreaExtra.objects.update_or_create(
                    base=area,
                    defaults={'type': area_type}
                )
                areas.append(area)
            # Now create all the Post objects:
            for election in elections:
                for area in areas:
                    organization = election.organization
                    party_set_slug = '2016_canton_' + slugify(area.name)
                    party_set = PartySet.objects.get(slug=party_set_slug)
                    post_role = election.for_post_role
                    post_prefix = {
                        'Alcalde': 'al-',
                        'Regidor': 're-',
                    }[post_role]
                    post_label = {
                        'Alcalde': 'Alcalde de {area_name}',
                        'Regidor': 'Regidor de {area_name}',
                    }[post_role].format(area_name=area.name)
                    post_slug = post_prefix + str(area.identifier)
                    try:
                        post_extra = PostExtra.objects.get(slug=post_slug)
                        post = post_extra.base
                    except PostExtra.DoesNotExist:
                        post = Post.objects.create(
                            label=post_label,
                            organization=organization,
                        )
                        post_extra = PostExtra.objects.create(
                            base=post,
                            slug=post_slug,
                        )
                    post.area = area
                    post.role = post_role
                    post.label = post_label
                    post.organization = organization
                    post.save()
                    post_extra.party_set = party_set
                    post_extra.save()
                    post_extra.elections.clear()
                    post_extra.elections.add(election)
