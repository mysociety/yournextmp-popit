# -*- coding: utf-8 -*-

from __future__ import print_function, unicode_literals

from datetime import date
import dateutil.parser
import csv
import json
from os.path import dirname, join
import re

import requests

from django.conf import settings
from django.contrib.auth.models import User
from django.core.files.storage import FileSystemStorage
from django.core.management.base import BaseCommand, CommandError

from candidates.utils import strip_accents
from candidates.views.version_data import get_change_metadata
from moderation_queue.models import QueuedImage
from elections.models import Election

UNKNOWN_PARTY_ID = 'unknown'
USER_AGENT = (
    'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 '
    '(KHTML, like Gecko) Ubuntu Chromium/38.0.2125.111 '
    'Chrome/38.0.2125.111Safari/537.36'
)

def get_post_data(api, origin_post,origin_district):
    from candidates.cache import get_post_cached
    from candidates.election_specific import AREA_DATA, AREA_POST_DATA
    if ("SUPLENTE" in origin_post):
        return False, False;

    ynr_election_id = {
        'DIPUTADO NACIONAL TITULAR':
        'diputados-argentina-paso-2015',
        'SENADOR NACIONAL TITULAR':
        'senadores-argentina-paso-2015',
        'PARLAMENTARIO MERCOSUR DISTRITO REGIONAL TITULAR':
        'parlamentarios-mercosur-regional-paso-2015',
        'PARLAMENTARIO MERCOSUR DISTRITO NACIONAL TITULAR':
        'parlamentarios-mercosur-unico-paso-2015'


    }[origin_post]
    ynr_election_data = Election.objects.get_by_slug(ynr_election_id)
    province = None

    if origin_district == "PARLAMENTARIO MERCOSUR DISTRITO NACIONAL(1)":
        post_id = 'pmeu'

    else:
        areas_by_name = AREA_DATA.areas_by_name[('PRV', '1')]
        area = areas_by_name[origin_district]
        post_id = AREA_POST_DATA.get_post_id(
            ynr_election_id, area['type'], area['id']
        )

    post_data = get_post_cached(api, post_id)['result']
    return ynr_election_data, post_data

def get_party_id(party_name):
    from candidates.election_specific import PARTY_DATA
    for p in PARTY_DATA.all_party_data:
       if (p.get("name").lower() == party_name.lower()):
         return p.get("id");
    return UNKNOWN_PARTY_ID;

def enqueue_image(person, user, image_url):
    r = requests.get(
        image_url,
        headers={
            'User-Agent': USER_AGENT,
        },
        stream=True
    )
    if not r.status_code == 200:
        message = "HTTP status code {0} when downloading {1}"
        raise Exception(message.format(r.status_code, image_url))
    storage = FileSystemStorage()
    suggested_filename = \
        'queued_image/{d.year}/{d.month:02x}/{d.day:02x}/ci-upload'.format(
            d=date.today()
        )
    storage_filename = storage.save(suggested_filename, r.raw)
    QueuedImage.objects.create(
        why_allowed=QueuedImage.OTHER,
        justification_for_use="Downloaded from {0}".format(image_url),
        decision=QueuedImage.UNDECIDED,
        image=storage_filename,
        person_id=person.id,
        user=user
    )

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


class Command(BaseCommand):

    args = 'USERNAME-FOR-UPLOAD'
    help = "Import inital candidate data"

    def handle(self, **options):
        from slumber.exceptions import HttpClientError, HttpServerError
        from candidates.election_specific import PARTY_DATA, shorten_post_label
        from candidates.models import PopItPerson
        from candidates.popit import create_popit_api_object

        api = create_popit_api_object()

        csv_filename = join(
            dirname(__file__), '..', '..','data', 'candidates.csv'
        )
        with open(csv_filename) as f:
            all_data = csv.DictReader(f)

            for candidate in all_data:
                vi_person_id = candidate['Distrito']+candidate['Numero Lista']+candidate['Posicion']+candidate['Cargo']+candidate['Nombre Lista']

                election_data, post_data = get_post_data(
                    api, candidate['Cargo'], candidate['Distrito']
                )
                if (election_data == False):
                    print("Skipping: "+ candidate['Cargo'] +", " + candidate['Distrito']+", " + candidate['Nombre'])
                    continue;

                name = candidate['Nombre']
                birth_date = None
                gender = None
                image_url = None

                person = get_existing_popit_person(vi_person_id)
                if person:
                    print("Found an existing person:", person.get_absolute_url())
                else:
                    print("No existing person, creating a new one:", name)
                    person = PopItPerson()

                # Now update fields from the imported data:
                person.name = name.split(",")[1] + " "  + name.split(",")[0]
                person.gender = gender
                if birth_date:
                    person.birth_date = str(birth_date)
                else:
                    person.birth_date = None
                standing_in_election = {
                    'post_id': post_data['id'],
                    'name': shorten_post_label(post_data['label']),
                    'party_list_position': candidate['Posicion'],
                }
                if 'area' in post_data:
                    standing_in_election['mapit_url'] = post_data['area']['identifier']

                person.standing_in = {
                    election_data.slug: standing_in_election
                }

                party_id = get_party_id(candidate["Partido"]);

                person.party_memberships = {
                    election_data.slug: {
                        'id': party_id,
                        'name': PARTY_DATA.party_id_to_name[party_id],
                    }
                }
                person.set_identifier('import-id', vi_person_id)
                change_metadata = get_change_metadata(
                    None,
                    'Imported candidate from CSV',
                )

                person.record_version(change_metadata)
                try:
                    person.save_to_popit(api)
                except HttpClientError as hce:
                    print("Got an HttpClientError:", hce.content)
                    raise
                except HttpServerError as hse:
                    print("The server error content was:", hse.content)
                    raise
