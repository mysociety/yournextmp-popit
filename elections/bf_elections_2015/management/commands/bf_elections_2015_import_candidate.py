# -*- coding: utf-8 -*-

from __future__ import print_function, unicode_literals

import dateutil.parser
import csv
from os.path import dirname, join
import re
import string
import codecs

import requests

from django.core.management.base import BaseCommand

from candidates.utils import strip_accents
from candidates.views.version_data import get_change_metadata

from elections.models import Election

UNKNOWN_PARTY_ID = 'unknown'
USER_AGENT = (
    'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 '
    '(KHTML, like Gecko) Ubuntu Chromium/38.0.2125.111 '
    'Chrome/38.0.2125.111Safari/537.36'
)


def get_post_data(api, election_id, province):
    from candidates.cache import get_post_cached
    from candidates.election_specific import AREA_DATA, AREA_POST_DATA
    ynr_election_data = Election.objects.get_by_slug(election_id)
    area_key = (ynr_election_data.area_types.first().name,
                 ynr_election_data.area_generation)
    areas_by_name = AREA_DATA.areas_by_name[area_key]
    if province != 'Burkina Faso':
        province = strip_accents(province).upper()
    area = areas_by_name[province]
    post_id = AREA_POST_DATA.get_post_id(
        election_id, area['type'], area['id']
    )
    post_data = get_post_cached(api, post_id)['result']
    return ynr_election_data, post_data


def get_existing_popit_person(vi_person_id):
    from candidates.models import PopItPerson
    from candidates.popit import get_search_url
    # See if this person already exists by searching for the
    # ID they were imported with:
    query_format = \
        'identifiers.identifier:"{id}" AND ' + \
        'identifiers.scheme:"{scheme}"'
    search_url = get_search_url(
        'persons',
        query_format.format(
            id=vi_person_id, scheme='import-id'
        ),
        embed='membership.organization'
    )
    results = requests.get(search_url).json()
    total = results['total']
    if total > 1:
        message = "Multiple matches for CI ID {0}"
        raise Exception(message.format(vi_person_id))
    if total == 0:
        return None
    # Otherwise there was exactly one result:
    return PopItPerson.create_from_dict(results['result'][0])


def get_party_data(party_name):
    from candidates.popit import get_search_url
    # See if this person already exists by searching for the
    # ID they were imported with:
    party_name = party_name.replace('/', '')
    party_name = party_name.decode('utf-8')
    query_format = \
        'name:"{name}"'
    search_url = get_search_url(
        'organizations',
        query_format.format(
            name=party_name
        )
    )
    print(party_name)
    results = requests.get(search_url).json()
    print(results)
    total = results['total']
    if total > 1:
        message = "Multiple matches for party {0}"
        raise Exception(message.format(party_name))
    if total == 0:
        return None
    # Otherwise there was exactly one result:
    return results['result'][0]


""" These functions taken from the csv docs -
https://docs.python.org/2/library/csv.html#examples"""
def unicode_csv_reader(unicode_csv_data, dialect=csv.excel, **kwargs):
    # csv.py doesn't do Unicode; encode temporarily as UTF-8:
    csv_reader = csv.reader(utf_8_encoder(unicode_csv_data),
                            dialect=dialect, **kwargs)
    for row in csv_reader:
        # decode UTF-8 back to Unicode, cell by cell:
        yield [cell.decode('utf-8') for cell in row]


def utf_8_encoder(unicode_csv_data):
    for line in unicode_csv_data:
        yield line.encode('utf-8')


class Command(BaseCommand):

    help = "Import inital candidate data"

    def handle(self, username=None, **options):
        from slumber.exceptions import HttpClientError
        from candidates.election_specific import PARTY_DATA, shorten_post_label
        from candidates.models import PopItPerson
        from candidates.popit import create_popit_api_object

        election_data = {
            'prv-2015': 'listedescandidatsauxelectionslegislativeslisteprovincialeanptic.csv',
            'nat-2015': 'listedescandidatsauxelectionslegislativesanptic.csv'
            }

        field_map = {
            'prv-2015': {
                'region': 1,
                'party': 4,
                'list_order': 5,
                'first_name': 7,
                'last_name': 6,
                'gender': 8,
                'birth_date': 9,
                'party_short': 3
            },
            'nat-2015': {
                'region': 0,
                'party': 2,
                'list_order': 3,
                'first_name': 5,
                'last_name': 4,
                'gender': 6,
                'birth_date': 7,
                'party_short': 2
            }
        }

        api = create_popit_api_object()

        party_id_missing = {}
        party_name_to_id = {}
        for party_id, party_name in PARTY_DATA.party_id_to_name.items():
            party_name_to_id[party_name] = party_id

        for election_id, filename in election_data.items():
            csv_filename = join(
                dirname(__file__), '..', '..', 'data', filename
            )

            fields = field_map[election_id]

            with codecs.open(csv_filename, 'r', encoding='windows-1252') as f:

                initial = True
                for candidate in unicode_csv_reader(f):
                    # skip header line
                    if initial:
                        initial = False
                        continue

                    region = candidate[fields['region']]
                    party = candidate[fields['party']]
                    party_list_order = candidate[fields['list_order']]
                    first_name = string.capwords(candidate[fields['first_name']])
                    last_name = string.capwords(candidate[fields['last_name']])
                    gender = candidate[fields['gender']]
                    birth_date = None

                    if candidate[fields['birth_date']] is not None:
                        birth_date = str(dateutil.parser.parse(
                            candidate[fields['birth_date']], dayfirst=True
                        ).date())

                    name = first_name + ' ' + last_name

                    id = '-'.join([
                        re.sub('[^\w]*', '', re.sub(r' ', '-', strip_accents(name.lower()))),
                        re.sub('[^\w]*', '', candidate[fields['party_short']].lower()),
                        birth_date
                    ])

                    # national candidate
                    if region == 'PAYS':
                        region = 'Burkina Faso'
                    election_data, post_data = get_post_data(
                        api, election_id, region
                    )

                    # debug
                    # tmp = '%s %s %s (%s) - %s (%s)' % ( id, first_name, last_name, party, region, post_data['label'] )
                    # print(tmp)

                    person = get_existing_popit_person(id)
                    if person:
                        # print("Found an existing person:", person.get_absolute_url())
                        pass
                    else:
                        print("No existing person, creating a new one:", name)
                        person = PopItPerson()

                    person.set_identifier('import-id', id)
                    person.family_name = last_name
                    person.given_name = first_name
                    person.name = name
                    person.gender = gender
                    if birth_date:
                        person.birth_date = str(birth_date)
                    else:
                        person.birth_date = None

                    standing_in_election = {
                        'post_id': post_data['id'],
                        'name': shorten_post_label(post_data['label']),
                        'party_list_position': party_list_order,
                    }

                    if 'area' in post_data:
                        standing_in_election['mapit_url'] = post_data['area']['identifier']

                    person.standing_in = {
                        election_data.slug: standing_in_election
                    }

                    change_metadata = get_change_metadata(
                        None,
                        'Imported candidate from CSV',
                    )

                    party_comp = re.sub(' +', ' ', party)
                    party_id = UNKNOWN_PARTY_ID
                    if party_comp in party_name_to_id.keys():
                        party_id = party_name_to_id[party_comp]
                        party = party_comp
                    else:
                        party_id = party_name_to_id['Unknown Party']
                        party = 'Unknown Party'

                    if party_id == UNKNOWN_PARTY_ID and party_comp not in party_id_missing.keys():
                        party_id_missing[party_comp] = 1

                    person.party_memberships = {
                        election_data.slug: {
                            'id': party_id,
                            'name': party,
                            'imported_name': party_comp
                        }
                    }

                    person.record_version(change_metadata)
                    try:
                        person.save_to_popit(api)
                    except HttpClientError as hce:
                        print("Got an HttpClientError:", hce.content)
                        raise

        if len(party_id_missing) > 0:
            print("Unmatched party names:")
            for name in party_id_missing.keys():
                print(name)
