from __future__ import print_function, unicode_literals

from datetime import datetime
import hashlib
from os.path import join
import re
from shutil import move
from tempfile import NamedTemporaryFile

from django.contrib.contenttypes.models import ContentType
from django.core.files.storage import FileSystemStorage
from django.core.management.base import BaseCommand
from django.conf import settings
from django.db import transaction
from django.utils.six.moves.urllib_parse import urlencode, urljoin

from images.models import Image
import magic
import mimetypes
from popolo.models import Organization
import requests
import dateutil.parser

from candidates.models import OrganizationExtra, PartySet, ImageExtra

emblem_directory = join(settings.BASE_DIR, 'data', 'party-emblems')
base_emblem_url = 'http://search.electoralcommission.org.uk/Api/Registrations/Emblems/'

def get_file_md5sum(filename):
    with open(filename, 'rb') as f:
        return hashlib.md5(f.read()).hexdigest()

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
        self.gb_parties = PartySet.objects.get(slug='gb')
        self.ni_parties = PartySet.objects.get(slug='ni')
        start = 0
        per_page = 50
        url = 'http://pefonline.electoralcommission.org.uk/api/search/Registrations'
        params = {
            'rows': per_page,
            'et': ["pp", "ppm"],
            'register': ["gb", "ni"],
            'regStatus': ["registered", "deregistered", "lapsed"],
        }
        with transaction.atomic():
            total = None
            while total is None or start <= total:
                params['start'] = start
                resp = requests.get(url + '?' + urlencode(params, doseq=True)).json()
                if total is None:
                    total = resp['Total']
                self.parse_data(resp['Result'])
                start += per_page

    def parse_data(self, ec_parties_data):
        for ec_party in ec_parties_data:
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
            # Does this party already exist?  If not, create a new one.
            try:
                party_extra = OrganizationExtra.objects \
                    .select_related('base') \
                    .get(slug=party_id)
                party = party_extra.base
                print("Got the existing party:", party.name.encode('utf-8'))
            except OrganizationExtra.DoesNotExist:
                party = Organization.objects.create(name=party_name)
                party_extra = OrganizationExtra.objects.create(
                    base=party, slug=party_id
                )
                print("Couldn't find {0}, creating a new party {1}".format(
                    party_id, party_name.encode('utf-8')
                ))

            party.name = party_name
            party.classification = 'Party'
            party.founding_date = party_founded
            party.party_dissolved = party_dissolved
            party_extra.register = register
            {
                'Great Britain': self.gb_parties,
                'Northern Ireland': self.ni_parties,
            }[register].parties.add(party)
            party.identifiers.update_or_create(
                scheme='electoral-commission',
                defaults={'identifier': ec_party_id}
            )
            party.other_names.filter(note='registered-description').delete()
            for d in get_descriptions(ec_party):
                value = d['description']
                translation = d['translation']
                if translation:
                    value = "{0} | {1}".format(value, translation)
                party.other_names.create(name=value, note='registered-description')
            self.upload_images(ec_party['PartyEmblems'], party_extra)
            party.save()
            party_extra.save()

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

    def upload_images(self, emblems, party_extra):
        content_type = ContentType.objects.get_for_model(party_extra)
        sort_emblems(emblems, party_extra.slug)
        primary = True
        for emblem in emblems:
            emblem_id = str(emblem['Id'])
            ntf = NamedTemporaryFile(delete=False)
            image_url = urljoin(base_emblem_url, emblem_id)
            r = requests.get(image_url)
            with open(ntf.name, 'w') as f:
                f.write(r.content)
            mime_type = self.mime_type_magic.from_file(ntf.name)
            extension = mimetypes.guess_extension(mime_type)
            leafname = 'Emblem_{0}{1}'.format(emblem_id, extension)
            desired_storage_path = join('images', leafname)
            fname = join(emblem_directory, leafname)
            move(ntf.name, fname)
            md5sum = get_file_md5sum(fname)
            ImageExtra.objects.update_or_create_from_file(
                fname,
                desired_storage_path,
                md5sum=md5sum,
                defaults={
                    'uploading_user':None,
                    'md5sum': md5sum,
                    'notes': emblem['MonochromeDescription'],
                    'base__source': 'The Electoral Commission',
                    'base__is_primary': primary,
                    'base__object_id': party_extra.id,
                    'base__content_type_id': content_type.id,
                }
            )
            primary = False

    def clean_id(self, party_id):
        party_id = re.sub(r'^PPm?\s*', '', party_id).strip()
        return "party:{0}".format(party_id)
