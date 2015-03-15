from datetime import datetime
import os
from os.path import join, splitext, exists
import re
import json
from slugify import slugify
from tempfile import NamedTemporaryFile
from urlparse import urljoin

from django.core.management.base import BaseCommand
from django.conf import settings

import requests
from slumber.exceptions import HttpServerError
import dateutil.parser

from candidates.popit import create_popit_api_object

from ..images import get_file_md5sum, image_uploaded_already

emblem_directory = join(settings.BASE_DIR, 'data', 'party-emblems')
base_emblem_url = 'http://openelectoralcommission.org.uk/party_images/'

def find_index(l, predicate):
    for i, e in enumerate(l):
        if predicate(e):
            return i
    return -1

IMAGES_TO_USE = {
    # Labour Party
    'party:53': 'Rose with the word Labour underneath',
    # Green Party
    'party:63': 'World with Petals and Green Party name English',
    # Another Green Party
    'party:305': 'Emblem 3',
    # Plaid Cymru
    'party:77': 'Emblem 3',
    # Ulster Unionist Party
    'party:83': 'Emblem 2',
    # Trade Unionist and Socialist Coalition
    'party:804': 'Emblem 3',
}

def sort_emblems(emblems, party_id):
    if party_id in IMAGES_TO_USE:
        generic_image_index = find_index(
            emblems,
            lambda e: e['description'] == IMAGES_TO_USE[party_id]
        )
        if generic_image_index < 0:
            raise Exception("Couldn't find the generic logo for " + party_id)
        emblems.insert(0, emblems.pop(generic_image_index))


class Command(BaseCommand):
    help = "Update parties from a CSV of party data"

    def handle(self, **options):
        self.api = create_popit_api_object()
        ntf = NamedTemporaryFile(delete=False)
        try:
            r = requests.get('http://openelectoralcommission.org.uk/parties/index.json')
            with open(ntf.name, 'w') as f:
                json.dump(r.json(), f)
            self.parse_data(ntf.name)
        finally:
            os.remove(ntf.name)

    def parse_data(self, json_file):
        with open(json_file) as f:
            for ec_party in json.load(f):
                ec_party_id = ec_party['party_id'].strip()
                # We're only interested in political parties:
                if not ec_party_id.startswith('PP'):
                    continue
                party_id = self.clean_id(ec_party_id)
                register = ec_party.get('register')
                if not register:
                    continue
                register = re.sub(r' \(minor party\)', '', register)
                party_name = self.clean_name(ec_party['party_name'])
                party_founded = self.clean_date(ec_party['registered_date'])
                if 'deregistered_date' in ec_party:
                    party_dissolved = self.clean_date(ec_party['deregistered_date'])
                else:
                    party_dissolved = '9999-12-31'
                party_data = {
                    'id': party_id,
                    'name': party_name,
                    'slug': slugify(party_name),
                    'classification': 'Party',
                    'founding_date': party_founded,
                    'dissolution_date': party_dissolved,
                    'register': register,
                    'identifiers': [
                        {
                            'identifier': ec_party_id,
                            'scheme': 'electoral-commission',
                        }
                    ]
                }
                try:
                    self.api.organizations.post(party_data)
                    self.upload_images(ec_party['emblems'], party_id)
                except HttpServerError as e:
                    if 'E11000' in e.content:
                        # Duplicate Party Found
                        self.api.organizations(party_id).put(party_data)
                        self.upload_images(ec_party['emblems'], party_id)
                    else:
                        raise

    def clean_date(self, date):
        return dateutil.parser.parse(date).strftime("%Y-%m-%d")

    def clean_name(self, name):
        return name.strip()

    def upload_images(self, emblems, party_id):
        image_upload_url = "{0}/{1}/organizations/{2}/image".format(
            self.api.get_url(), self.api.get_api_version(), party_id
        )
        sort_emblems(emblems, party_id)
        for emblem in emblems:
            fname = join(emblem_directory, emblem['image'])
            if not exists(fname):
                image_url = urljoin(base_emblem_url, emblem['image'])
                r = requests.get(image_url)
                with open(fname, 'w') as f:
                    f.write(r.content)
            if not image_uploaded_already(
                self.api.organizations,
                party_id,
                fname
            ):
                mime_type = {
                    '.gif': 'image/gif',
                    '.bmp': 'image/x-ms-bmp',
                    '.jpg': 'image/jpeg',
                    '.jpeg': 'image/jpeg',
                    '.png': 'image/png',
                }[splitext(fname)[1]]
                md5sum = get_file_md5sum(fname)
                with open(fname, 'rb') as f:
                    requests.post(
                        image_upload_url,
                        headers={
                            'Apikey': self.api.api_key
                        },
                        files={
                            'image': f
                        },
                        data={
                            'notes': emblem['description'],
                            'source': 'The Electoral Commission',
                            'id': emblem['id'],
                            'md5sum': md5sum,
                            'mime_type': mime_type,
                        }
                    )

    def clean_id(self, party_id):
        party_id = re.sub(r'^PPm?\s*', '', party_id).strip()
        return "party:{0}".format(party_id)
