# -*- coding: utf-8 -*-

from __future__ import print_function, unicode_literals

import csv
import re
import requests

from django.core.management.base import BaseCommand

from django.utils.text import slugify

from candidates.models import PartySet, OrganizationExtra
from popolo import models as popolo_models
from popolo.importers.popit import PopItImporter


def fix_whitespace(s):
    s = s.strip()
    return re.sub(r'(?ms)\s+', ' ', s)


"""
Takes an argument of a CSV file which should have 3 columns:

    1: Name of party
    2: ID of party (optional)
    3: Comma separated list of Cantons the party is standing in

The ID is the "Cédula Jurídica" and is added as an Identifier and
used as the slug, otherwise we fall back to the slugified name.

It expects the CSV file to have NO header row.

It will create, or update, a party for each row in the CSV and
a party set for each Canton, adding the party to the party sets
for the Cantons in which the party is standing.
"""


class Command(BaseCommand):
    help = 'Create or update parties from a CSV file'

    def add_arguments(self, parser):
        parser.add_argument('CSV-FILENAME')

    def add_id(self, party, party_id):
        party.identifiers.update_or_create(
            scheme='cedula-juridica',
            defaults={'identifier': party_id}
        )

    def generate_party_sets(self):
        mapit_url = 'http://international.mapit.mysociety.org/areas/CRCANTON'

        cantons = requests.get(mapit_url).json()

        for canton_id, canton_data in cantons.items():
            name = canton_data['name']
            self.get_party_set(name)

    def update_party(self, party_data):
        # strip any bracketed information from the end of the name
        # as it's information about party initials or canton
        name = re.search(
            r'^([^(]*)\(?',
            fix_whitespace(party_data[0])
        ).group(1).decode('utf-8')
        party_id = fix_whitespace(party_data[1])

        # remove the (13/81) information text from the end of
        # the canton list.
        canton_list = re.search(
            r'^([^(]*)\(?',
            fix_whitespace(party_data[2])
        ).group(1)
        cantons = canton_list.split(',')

        # if posible we should use the official id but failing that fall
        # back to a slugified name
        if party_id != '':
            slug = party_id
        else:
            slug = slugify(name)

        try:
            # slug should be consistent and not have any
            # encoding issues
            org_extra = OrganizationExtra.objects.get(
                slug=slug
            )
            org = org_extra.base
            print("found existing party {0}".format(name))
        except OrganizationExtra.DoesNotExist:
            org = popolo_models.Organization.objects.create(
                name=name,
                classification='Party'
            )

            OrganizationExtra.objects.create(
                base=org, slug=slug
            )
            print("created new party {0}".format(name))

        if party_id != '':
            self.add_id(org, party_id)

        for canton in cantons:
            canton = canton.decode('utf-8')
            party_set = self.get_party_set(canton)
            if not org.party_sets.filter(slug=party_set.slug):
                print("adding party set {0}".format(party_set.slug))
                org.party_sets.add(party_set)

    def get_party_set(self, canton_name):
        canton = fix_whitespace(canton_name)
        party_set_slug = "2016_canton_{0}".format(slugify(canton))
        party_set_name = "2016 parties in {0} Canton".format(canton)
        try:
            return PartySet.objects.get(slug=party_set_slug)
        except PartySet.DoesNotExist:
            self.stdout.write("Couldn't find the party set '{0}'".format(
                party_set_slug
            ))
            return PartySet.objects.create(
                slug=party_set_slug, name=party_set_name
            )

    def handle(self, **options):
        self.importer = PopItImporter()

        self.generate_party_sets()

        with open(options['CSV-FILENAME']) as f:
            csv_reader = csv.reader(f)
            for party_data in csv_reader:
                self.update_party(party_data)
