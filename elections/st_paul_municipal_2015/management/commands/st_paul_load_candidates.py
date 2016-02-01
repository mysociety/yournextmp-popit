from __future__ import print_function, unicode_literals

import requests
import csv

from io import StringIO

from django.core.management.base import BaseCommand
from django.template.defaultfilters import slugify

from candidates.views.version_data import get_change_metadata
from elections.models import Election

import memcache

UNKNOWN_PARTY_ID = 'unknown'
GOOGLE_DOC_ID = '1yme9Y9Vt876-cVR9bose3QDqF7j8hqLnWYEjO3HUqXs'

def get_existing_popit_person(person_id):
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
            id=person_id, scheme='import-id'
        ),
        embed='membership.organization'
    )
    results = requests.get(search_url).json()
    total = results['total']
    if total > 1:
        message = "Multiple matches for CI ID {0}"
        raise Exception(message.format(person_id))
    if total == 0:
        return None
    # Otherwise there was exactly one result:
    return PopItPerson.create_from_dict(results['result'][0])

class Command(BaseCommand):
    help = "Load or update St. Paul candidates from Google docs"

    def handle(self, **options):
        from slumber.exceptions import HttpClientError
        from candidates.cache import get_post_cached, UnknownPostException
        from candidates.election_specific import PARTY_DATA, shorten_post_label
        from candidates.models import PopItPerson
        from candidates.popit import create_popit_api_object

        spreadsheet_url = 'https://docs.google.com/spreadsheets/d/{0}/pub?output=csv'\
                              .format(GOOGLE_DOC_ID)

        candidate_list = requests.get(spreadsheet_url)

        content = StringIO(candidate_list.text)
        reader = csv.DictReader(content)

        api = create_popit_api_object()

        for row in reader:

            try:
                election_data = Election.objects.get_by_slug('council-member-2015')
                ocd_division = election_data.post_id_format.format(area_id=row['Ward'])
                post_data = get_post_cached(api, ocd_division)['result']
            except (UnknownPostException, memcache.Client.MemcachedKeyCharacterError):
                election_data = Election.objects.get_by_slug('school-board-2015')
                post_data = get_post_cached(api, election_data.post_id_format)['result']

            person_id = slugify(row['Name'])

            person = get_existing_popit_person(person_id)

            if person:
                print("Found an existing person:", row['Name'])
            else:
                print("No existing person, creating a new one:", row['Name'])
                person = PopItPerson()

            person.name = row['Name']

            # TODO: Get these attributes in the spreadsheet
            # person.gender = gender
            # if birth_date:
            #     person.birth_date = str(birth_date)
            # else:
            #     person.birth_date = None

            person.email = row['Campaign Email']
            person.facebook_personal_url = row["Candidate's Personal Facebook Profile"]
            person.facebook_page_url = row['Campaign Facebook Page']


            person.twitter_username = row['Campaign Twitter']\
                                          .replace('N', '')\
                                          .replace('N/A', '')\
                                          .replace('http://twitter.com/', '')\
                                          .replace('https://twitter.com/', '')

            person.linkedin_url = row['LinkedIn']
            person.homepage_url = row['Campaign Website\n']

            standing_in_election = {
                'post_id': post_data['id'],
                'name': shorten_post_label(post_data['label']),
            }
            if 'area' in post_data:
                standing_in_election['mapit_url'] = post_data['area']['identifier']
            person.standing_in = {
                election_data.slug: standing_in_election
            }

            if 'dfl' in row['Party'].lower():
                party_id = 'party:101'
            elif 'green' in row['Party'].lower():
                party_id = 'party:201'
            elif 'independence' in row['Party'].lower():
                party_id = 'party:301'
            else:
                party_id = 'party:401'


            party_name = PARTY_DATA.party_id_to_name[party_id]

            person.party_memberships = {
                election_data.slug: {
                    'id': party_id,
                    'name': party_name,
                }
            }

            person.set_identifier('import-id', person_id)
            change_metadata = get_change_metadata(
                None,
                'Imported candidate from Google Spreadsheet',
            )

            person.record_version(change_metadata)
            try:
                person.save_to_popit(api)

                # TODO: Get candidate Images
                # if image_url:
                #     enqueue_image(person, user, image_url)
            except HttpClientError as hce:
                print("Got an HttpClientError:", hce.content)
                raise
