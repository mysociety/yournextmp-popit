from __future__ import unicode_literals

import json

from django.core.management.base import BaseCommand
from django.core.exceptions import ObjectDoesNotExist

from candidates.models import PartySet, OrganizationExtra
from popolo import models as popolo_models
from popolo.importers.popit import PopItImporter

from compat import input


class Command(BaseCommand):
    help = 'Create or update parties from a Popolo JSON file'

    def add_arguments(self, parser):
        parser.add_argument('JSON-FILENAME')
        parser.add_argument('--party-set', default='default')

    def add_related_objects(self, org, attr, related_data_list, get_kwargs):
        related_manager = getattr(org, attr)
        for related_data in related_data_list:
            kwargs = get_kwargs(related_data)
            try:
                related_manager.get(**kwargs)
            except ObjectDoesNotExist:
                related_manager.create(**kwargs)

    def update_party(self, party_data, party_set):
        kwargs = {}
        for k in (
            'name', 'summary', 'description', 'classification',
            'founding_date', 'dissolution_date',
        ):
            v = party_data.get(k)
            if v:
                kwargs[k] = v
        try:
            org_extra = OrganizationExtra.objects.get(
                slug=party_data['id']
            )
            org = org_extra.base
            for k, v in kwargs.items():
                setattr(org, k, v)
            if not org.party_sets.filter(slug=party_set.slug):
                org.party_sets.add(party_set)
        except OrganizationExtra.DoesNotExist:
            org = popolo_models.Organization.objects.create(**kwargs)
            org_extra = OrganizationExtra.objects.create(
                base=org, slug=party_data['id']
            )
            org.party_sets.add(party_set)
        # Now make sure any related objects exist:
        for k, get_kwargs in [
                ('contact_details', self.importer.make_contact_detail_dict),
                ('identifiers', self.importer.make_identifier_dict),
                ('links', self.importer.make_link_dict),
                ('sources', self.importer.make_source_dict),
                ('other_names', self.importer.make_other_name_dict),
        ]:
            if len(party_data.get(k, [])) > 0:
                self.add_related_objects(
                    org,
                    k,
                    party_data[k],
                    get_kwargs
                )


    def get_party_set(self, requested_party_set_slug):
        try:
            return PartySet.objects.get(slug=requested_party_set_slug)
        except PartySet.DoesNotExist:
            self.stdout.write("Couldn't find the party set '{0}'".format(
                requested_party_set_slug
            ))
            all_party_sets = PartySet.objects.values_list('slug', flat=True)
            if PartySet.objects.exists():
                self.stdout.write("You might have meant one of these:")
                for other_party_set_slug in all_party_sets:
                    self.stdout.write("  " + other_party_set_slug)
            self.stdout.write(
                "Create the party set '{0}'? (y/n) ".format(
                    requested_party_set_slug
                ),
                ending=''
            )
            response = input()
            if response.strip().lower() != 'y':
                self.stderr.write("Exiting.")
                return
            self.stdout.write('What is the full name of the party set? ')
            response = input()
            return PartySet.objects.create(
                slug=requested_party_set_slug, name=response
            )

    def handle(self, **options):
        self.importer = PopItImporter()
        party_set = self.get_party_set(options['party_set'])
        with open(options['JSON-FILENAME']) as f:
            for party_data in json.load(f):
                self.update_party(party_data, party_set)
