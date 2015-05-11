from datetime import datetime
import os
from os.path import join
import re
import json
from shutil import move
from slugify import slugify
from tempfile import NamedTemporaryFile
from urllib import urlencode
from urlparse import urljoin

from django.core.management.base import BaseCommand
from django.conf import settings

import magic
import mimetypes
import requests
from slumber.exceptions import HttpServerError
import dateutil.parser

from candidates.models import PopItPerson
from candidates.popit import create_popit_api_object

from ..images import get_file_md5sum, image_uploaded_already

emblem_directory = join(settings.BASE_DIR, 'data', 'party-emblems')
base_emblem_url = 'http://search.electoralcommission.org.uk/Api/Registrations/Emblems/'

def find_index(l, predicate):
    for i, e in enumerate(l):
        if predicate(e):
            return i
    return -1

IMAGES_TO_USE = {
    # Labour Party
    'party:53': 'Rose with the word Labour underneath',
    # Green Party
    'party:63': 'World with petals and Green Party name English',
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
            lambda e: e['MonochromeDescription'] == IMAGES_TO_USE[party_id]
        )
        if generic_image_index < 0:
            raise Exception("Couldn't find the generic logo for " + party_id)
        emblems.insert(0, emblems.pop(generic_image_index))

def get_descriptions(party):
    return [
        {'description': d['Description'],
         'translation': d['Translation']}
        for d in party['PartyDescriptions']
    ]

class Command(BaseCommand):
    help = "Update parties from a CSV of party data"

    def handle(self, **options):
        self.mime_type_magic = magic.Magic(mime=True)
        self.api = create_popit_api_object()
        start = 0
        per_page = 50
        url = 'http://pefonline.electoralcommission.org.uk/api/search/Registrations'
        params = {
            'rows': per_page,
            'et': ["pp", "ppm"],
            'register': ["gb", "ni"],
            'regStatus': ["registered", "deregistered", "lapsed"],
        }
        total = None
        while total is None or start <= total:
            ntf = NamedTemporaryFile(delete=False)
            params['start'] = start
            try:
                resp = requests.get(url + '?' + urlencode(params, doseq=True)).json()
                if total is None:
                    total = resp['Total']
                with open(ntf.name, 'w') as f:
                    json.dump(resp['Result'], f)
                self.parse_data(ntf.name)
            finally:
                os.remove(ntf.name)
            start += per_page

    def parse_data(self, json_file):
        with open(json_file) as f:
            for ec_party in json.load(f):
                ec_party_id = ec_party['ECRef'].strip()
                # We're only interested in political parties:
                if not ec_party_id.startswith('PP'):
                    continue
                party_id = self.clean_id(ec_party_id)
                if ec_party['RegulatedEntityTypeName'] == 'Minor Party':
                    register = ec_party['RegisterNameMinorParty'].replace(
                        ' (minor party)', ''
                    )
                else:
                    register = ec_party['RegisterName']
                party_name, party_dissolved = self.clean_name(ec_party['RegulatedEntityName'])
                party_founded = self.clean_date(ec_party['ApprovedDate'])
                party_data = {
                    'id': party_id,
                    'name': party_name,
                    'slug': slugify(party_name),
                    'classification': 'Party',
                    'descriptions': get_descriptions(ec_party),
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
                    self.upload_images(ec_party['PartyEmblems'], party_id)
                except HttpServerError as e:
                    if 'E11000' in e.content:
                        # Duplicate Party Found
                        self.api.organizations(party_id).put(party_data)
                        self.upload_images(ec_party['PartyEmblems'], party_id)
                    else:
                        raise
                organization_with_memberships = \
                    self.api.organizations(party_id).get(embed='membership.person')['result']
                # Make sure any members of these parties are
                # invalidated from the cache so that the embedded
                # party information when getting posts and persons is
                # up-to-date:
                for membership in organization_with_memberships.get(
                        'memberships', []
                ):
                    person = PopItPerson.create_from_dict(membership['person_id'])
                    person.invalidate_cache_entries()

    def clean_date(self, date):
        timestamp = re.match(
            r'\/Date\((\d+)\)\/', date).group(1)
        dt = datetime.fromtimestamp(int(timestamp) / 1000.)
        return dt.strftime("%Y-%m-%d")

    def clean_name(self, name):
        name = name.strip()
        if not 'de-registered' in name.lower():
            return name, '9999-12-31'

        match = re.match(
            r'(.+)\[De-registered ([0-9]+/[0-9]+/[0-9]+)\]', name)
        name, deregistered_date = match.groups()
        name = re.sub(r'\([Dd]e-?registered [^\)]+\)', '', name)
        deregistered_date = dateutil.parser.parse(
            deregistered_date, dayfirst=True).strftime("%Y-%m-%d")

        return name.strip(), deregistered_date

    def upload_images(self, emblems, party_id):
        image_upload_url = "{0}/{1}/organizations/{2}/image".format(
            self.api.get_url(), self.api.get_api_version(), party_id
        )
        sort_emblems(emblems, party_id)
        for emblem in emblems:
            emblem_id = str(emblem['Id'])
            ntf = NamedTemporaryFile(delete=False)
            image_url = urljoin(base_emblem_url, emblem_id)
            r = requests.get(image_url)
            with open(ntf.name, 'w') as f:
                f.write(r.content)
            mime_type = self.mime_type_magic.from_file(ntf.name)
            extension = mimetypes.guess_extension(mime_type)
            fname = join(emblem_directory, 'Emblem_{0}{1}'.format(emblem_id, extension))
            move(ntf.name, fname)
            if not image_uploaded_already(
                self.api.organizations,
                party_id,
                fname
            ):
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
                            'notes': emblem['MonochromeDescription'],
                            'source': 'The Electoral Commission',
                            'id': emblem_id,
                            'md5sum': md5sum,
                            'mime_type': mime_type,
                            'created': None,
                        }
                    )

    def clean_id(self, party_id):
        party_id = re.sub(r'^PPm?\s*', '', party_id).strip()
        return "party:{0}".format(party_id)
