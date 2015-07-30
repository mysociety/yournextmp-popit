# -*- coding: utf-8 -*-

from datetime import date
import dateutil.parser
import csv
import json
from os.path import dirname, join
import re

import requests
from slumber.exceptions import HttpClientError

from django.conf import settings
from django.contrib.auth.models import User
from django.core.files.storage import FileSystemStorage
from django.core.management.base import BaseCommand, CommandError

from candidates.cache import get_post_cached
from candidates.election_specific import MAPIT_DATA, PARTY_DATA, AREA_POST_DATA
from candidates.models import PopItPerson
from candidates.popit import create_popit_api_object, get_search_url
from candidates.utils import strip_accents
from candidates.views.version_data import get_change_metadata
from moderation_queue.models import QueuedImage

UNKNOWN_PARTY_ID = 'unknown'
USER_AGENT = (
    'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 '
    '(KHTML, like Gecko) Ubuntu Chromium/38.0.2125.111 '
    'Chrome/38.0.2125.111Safari/537.36'
)

def get_post_data(api, origin_post,origin_district):
    ynr_election_id = {
        u'DIPUTADO NACIONAL TITULAR':
        'diputados-argentina-paso-2015',
        u'SENADOR NACIONAL TITULAR':
        'senadores-argentina-paso-2015',
    }[origin_post]
    ynr_election_data = settings.ELECTIONS[ynr_election_id]
    ynr_election_data['id'] = ynr_election_id
    province = None

    mapit_areas_by_name = MAPIT_DATA.areas_by_name[('PRV', 1)]
    mapit_area = mapit_areas_by_name[origin_district]
    post_id = AREA_POST_DATA.get_post_id(
        ynr_election_id, mapit_area['type'], mapit_area['id']
    )

    post_data = get_post_cached(api, post_id)['result']
    return ynr_election_data, post_data

def get_party_id(party_name):
    return next((id for id, name in PARTY_DATA.party_choices.items() if name == party_name), UNKNOWN_PARTY_ID)

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
        raise Exception, message.format(r.status_code, image_url)
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
        popit_person_id=person.id,
        user=user
    )

def get_existing_popit_person(vi_person_id):
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

    def handle(self, username=None, **options):

        if username is None:
            message = "You must supply the name of a user to be associated with the image uploads."
            raise CommandError(message)
        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            message = "No user with the username '{0}' could be found"
            raise CommandError(message.format(username))

        api = create_popit_api_object()

        csv_filename = join(
            dirname(__file__), '..', '..','data', 'candidates.csv'
        )
        with open(csv_filename) as f:
            all_data = csv.DictReader(f)

            for candidate in all_data:
                print ",".join(candidate)
                vi_person_id = candidate['Distrito']+candidate['Numero Lista']+candidate['Posicion']

                election_data, post_data = get_post_data(
                    api, candidate['Cargo'], candidate['Distrito']
                )
                name = candidate['Nombre']
                birth_date = None
                gender = None
                image_url = None

                person = get_existing_popit_person(vi_person_id)
                if person:
                    print "Found an existing person:", person.get_absolute_url()
                else:
                    print "No existing person, creating a new one:", name
                    person = PopItPerson()

                # Now update fields from the imported data:
                person.name = name
                person.gender = gender
                if birth_date:
                    person.birth_date = str(birth_date)
                else:
                    person.birth_date = None
                standing_in_election = {
                    'post_id': post_data['id'],
                    'name': AREA_POST_DATA.shorten_post_label(
                        election_data['id'],
                        post_data['label'],
                    ),
                }
                if 'area' in post_data:
                    standing_in_election['mapit_url'] = post_data['area']['identifier']
                person.standing_in = {
                    election_data['id']: standing_in_election
                }

                party_id = get_party_id(candidate["Partido"]);

                person.party_memberships = {
                    election_data['id']: {
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
                    if image_url:
                        enqueue_image(person, user, image_url)
                except HttpClientError as hce:
                    print "Got an HttpClientError:", hce.content
                    raise
