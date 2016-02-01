# Take the scraped PPC data and try to import it into PopIt.
#
# It looks for someone with the same name by searching PopIt, and, if
# matches are found, asks the user whether they're the same person.
# This decision is recorded in a JSON file so you should only need to
# make that choice once.
#
# TODO: add a --noinput option, which won't ask for input, but instead
# output text and return an error; this will be useful for running
# this job from cron - if you get an email from cron, you'll need to
# run the script manually to make those decisions.

from __future__ import print_function, unicode_literals

from optparse import make_option
import os
from os.path import join, exists
import re
import json

from django.core.management.base import BaseCommand
from django.conf import settings

import requests

from candidates.views.version_data import get_change_metadata

from compat import input

from ..images import get_file_md5sum

party_slug_to_popit_party = {
    'labour': {
        'name': 'Labour Party',
        'id': 'party:53',
    },
    'conservatives': {
        'name': 'Conservative Party',
        'id': 'party:52',
    },
    'libdem': {
        'name': 'Liberal Democrats',
        'id': 'party:90',
    }
}

constituency_corrections = {
    'Berwick': 'Berwick-upon-Tweed',
    'Chester': 'City of Chester',
    'Cotswolds': 'The Cotswolds',
    'Dover and Deal': 'Dover',
    'Harborough, Oadby and Wigston': 'Harborough',
    'Hull North': 'Kingston upon Hull North',
    'Hull West and Hessle': 'Kingston upon Hull West and Hessle',
    'Isle of Wright': 'Isle of Wight',
    'Liverpool, Wavetree': 'Liverpool, Wavertree',
    'Liverpool Wavetree': 'Liverpool, Wavertree',
    'Mid-Norfolk': 'Mid Norfolk',
    'Richmond': 'Richmond (Yorks)',
    'Sittingbourne and Sheppy': 'Sittingbourne and Sheppey',
    'Stratford-upon-Avon': 'Stratford-on-Avon',
    'West Cornwall and Scilly': 'St Ives',
    'Weston Super Mare': 'Weston-Super-Mare',
    'Canterbury and Whitstable': 'Canterbury',
    'Brent Central - Liberal Democrat Race Equality Champion': 'Brent Central',
    'Coatbridge, Chryston, Bellshill': 'Coatbridge, Chryston and Bellshill',
    'East Kilbride': 'East Kilbride, Strathaven and Lesmahagow',
    'Newcastle under Lyme': 'Newcastle-under-Lyme',
    'North Northamptonshire': 'Northampton South',
}

def cons_key(s):
    return re.sub(r',', '', s).lower()


class UnknownConstituencyException(Exception):
    pass

def get_constituency_from_name(constituency_name, constituency_lookup):
    name = re.sub(r'\xA0', ' ', constituency_name)
    name = re.sub(r' & ', ' and ', name)
    name = re.sub(r'(?i)candidate for ', '', name)
    name = constituency_corrections.get(name, name)
    try:
        mapit_data = constituency_lookup[cons_key(name)]
    except KeyError:
        message = "Unknown constituency; {0} - consider adding a correction for {1}"
        raise UnknownConstituencyException(message.format(
            cons_key(name), name
        ))
    post_id = str(mapit_data['id'])
    return {
        'post_id': post_id,
        'name': mapit_data['name'],
        'mapit_url': 'http://mapit.mysociety.org/area/{0}'.format(post_id),
    }

ppc_data_directory = join(
    settings.BASE_DIR,
    'data',
    'UK-Political-Parties',
    'ppcs',
    'json'
)

human_decisions_filename = join(
    settings.BASE_DIR,
    'data',
    'human-ppc-decisions.json'
)

def get_human_decisions():
    with open(human_decisions_filename) as f:
        return json.load(f)

def write_human_decisions(human_decisions):
    output = json.dumps(human_decisions, indent=4, sort_keys=True)
    output = re.sub(r'(?ms)\s*$', '', output)
    with open(human_decisions_filename, 'w') as f:
        f.write(output)

def record_human_decision(ppc_dict, popit_person_id, same):
    human_decisions = get_human_decisions()
    human_decisions.append({
        'same_person': same,
        'ppc': ppc_dict,
        'popit_person_id': popit_person_id,
    })
    write_human_decisions(human_decisions)

def get_human_decision(ppc_data):
    fields_to_match = ['party_slug', 'constituency', 'name']
    matching_decisions = []
    for decision in get_human_decisions():
        if all(decision['ppc'][k] == ppc_data[k] for k in fields_to_match):
            matching_decisions.append(decision)
    return matching_decisions

def merge_person_data(old_data, new_data):
    data = old_data.copy()
    standing_in = data.get('standing_in', {})
    party_memberships = data.get('party_memberships', {})
    standing_in.update(new_data.get('standing_in', {}))
    party_memberships.update(new_data.get('party_memberships', {}))
    data.update(new_data)
    data['standing_in'] = standing_in
    data['party_memberships'] = party_memberships
    return data

def get_ppc_url_from_popit_result(popit_result):
    links = popit_result.get('links', [])
    for link in links:
        if link.get('note') == 'party PPC page':
            return link.get['url']
    return None

def key_value_appeared_in_previous_version(key, value, versions):
    for version in versions:
        value_from_old_version = version['data'].get(key)
        if value_from_old_version == value:
            return True
    else:
        return False


class Command(BaseCommand):
    help = "Import scraped PPC data"

    option_list = BaseCommand.option_list + (
        make_option('--check', action='store_true', dest='check', help='Check constituency names'),
    )

    # Currently unused:
    #
    #     "region",
    #     "full_url",
    #     "path",
    #     "phone",
    #     "slug",
    #     "address",
    #     "current_mp",
    #     "blog_url",
    #     "campaign_url",
    #     "biography_url",

    def get_person_data_from_ppc(self, ppc_data):
        return {
            'name': ppc_data.get('name', ''),
            'email': ppc_data.get('email', ''),
            'birth_date': None,
            'twitter_username': ppc_data.get('twitter_username', ''),
            'facebook_personal_url': ppc_data.get('facebook_url', ''),
            'homepage_url': ppc_data.get('homepage_url', ''),
            'party_ppc_page_url': ppc_data.get('full_url', ''),
            'standing_in': {
                '2015': ppc_data['constituency_object'],
            },
            'party_memberships': {
                '2015': ppc_data['party_object'],
            }
        }

    def upload_person_image(self, person_id, image_filename, original_url):
        # Find the md5sum of the image filename, to use as an ID:
        md5sum = get_file_md5sum(image_filename)
        image_upload_url = "{0}/{1}/persons/{2}/image".format(
            self.api.get_url(), self.api.get_api_version(), person_id
        )
        source = 'Via the official party PPC page, based on {0}'.format(original_url)
        with open(image_filename, 'rb') as f:
            requests.post(
                image_upload_url,
                headers={
                    'Apikey': self.api.api_key
                },
                files={
                    'image': f
                },
                data={
                    'notes': 'md5sum:' + md5sum,
                    'source': source,
                    'mime_type': 'image/png',
                }
            )

    def update_popit_person(self, popit_person_id, ppc_data, image_filename):
        from candidates.models import PopItPerson
        from ..images import image_uploaded_already
        # Get the existing data first:
        person_data, _ = self.get_person(popit_person_id)
        previous_versions = person_data.pop('versions')
        new_person_data = self.get_person_data_from_ppc(ppc_data)
        # Remove any empty keys, we don't want to overwrite exiting
        # data with nothing:
        keys = new_person_data.keys()
        warnings = []
        for key in keys:
            if not new_person_data[key]:
                del new_person_data[key]
            # Also make sure that we don't overwrite any existing
            # fields that are filled in with different values:
            if key not in ('standing_in', 'party_memberships'):
                new_person_data_value = new_person_data.get(key)
                person_data_value = person_data.get(key)
                if person_data_value and new_person_data_value and new_person_data_value != person_data_value:
                    if key_value_appeared_in_previous_version(
                        key,
                        new_person_data_value,
                        previous_versions
                    ):
                        warning_message = "[{0}] it looks as if a previous "
                        warning_message += "version had {1}, so not "
                        warning_message += "overwriting the current value {2}"
                        warnings.append(warning_message.format(
                            key,
                            new_person_data_value,
                            person_data_value
                        ))
                        del new_person_data[key]
                    else:
                        warnings.append("[{0}] replacing      {1}".format(key, person_data_value))
                        warnings.append("[{0}] with new value {1}".format(key, new_person_data_value))
        if warnings:
            print("Warnings for person/{0} {1}".format(
                popit_person_id, person_data['name']
            ).encode('utf-8'))
            for warning in warnings:
                print("  ...", warning.encode('utf-8'))
        merged_person_data = merge_person_data(person_data, new_person_data)
        change_metadata = get_change_metadata(
            None,
            'Updated candidate from official PPC data ({0})'.format(ppc_data['party_slug']),
        )
        person = PopItPerson.create_from_reduced_json(merged_person_data)
        person.record_version(change_metadata)
        person_id = person.save_to_popit(self.api)
        if image_filename:
            if image_uploaded_already(self.api.persons, person_id, image_filename):
                print("That image has already been uploaded!")
            else:
                print("Uploading image...")
                self.upload_person_image(person_id, image_filename, ppc_data['image_url'])
        person.invalidate_cache_entries()
        return person_id

    def add_popit_person(self, ppc_data, image_filename):
        from candidates.models import PopItPerson
        change_metadata = get_change_metadata(
            None,
            'Created new candidate from official PPC data ({0})'.format(ppc_data['party_slug']),
        )
        person_data = self.get_person_data_from_ppc(ppc_data)
        person = PopItPerson.create_from_reduced_json(person_data)
        person.record_version(change_metadata)
        person_id = person.save_to_popit(self.api)
        if image_filename:
            self.upload_person_image(person_id, image_filename, ppc_data['image_url'])
        person.invalidate_cache_entries()
        return person_id

    def already_added_for_2015(self, ppc_data, popit_result):
        '''True if ppc_data matches popit_result, and is already marked as standing

        This method returns True if popit_result seems to be the same
        person referred to as ppc_data and that person's already
        marked as standing in 2015 (in the right constituency). It
        returns None if popit_result is malformed or they've been
        since marked as "known not to be standing in 2015". Otherwise,
        this returns False.'''
        standing_in = popit_result.get('standing_in')
        # Due to this PopIt bug https://github.com/mysociety/popit/issues/710
        # we sometimes end up with this malformed standing_in:
        if standing_in is None:
            return None
        standing_in_2015 = standing_in.get('2015', {})
        # If standing_in_2015 is None, then they were added but
        # someone has since marked them as not standing; return None
        # and deal with that case specially:
        if standing_in_2015 is None:
            return None
        # Now just check if their name, party and constituency in 2015
        # match:
        popit_constituency_name_2015 = standing_in_2015.get('name')
        popit_party_id_2015 = popit_result['party_memberships'].get('2015', {}).get('id')
        return (ppc_data['name'] == popit_result['name'] and
                ppc_data['party_object']['id'] == popit_party_id_2015 and
                ppc_data['constituency_object']['name'] == popit_constituency_name_2015)

    def already_matched_to_a_person(self, ppc_data, popit_person_id):
        decisions = get_human_decision(ppc_data)
        for decision in decisions:
            if popit_person_id == decision['popit_person_id']:
                return decision['same_person']
        return None

    def decision_from_user(self, ppc_data, popit_result):
        # Ask whether the PPC is the same as this person from the
        # PopIt search results:
        print("--------------------------------------------------------")
        print("Is this PPC ...")
        print("        Name:", ppc_data['name'].encode('utf-8'))
        if 'email' in ppc_data:
            print("        Email:", ppc_data['email'])
        print("        Party:", ppc_data['party_slug'])
        print("        Constituency:", ppc_data['constituency'])
        if 'full_url' in ppc_data:
            print("        PPC URL:", ppc_data['full_url'])
        print("... the same as this person from PopIt:")
        print("        PopIt URL:", popit_result['html_url'])
        print("        Name:", popit_result['name'].encode('utf-8'))
        if 'email' in popit_result:
            print("        Email:", popit_result['email'])
        for year in popit_result['party_memberships']:
            print("        Party in {0}: {1}".format(
                year, popit_result['party_memberships'][year]['name']
            ))
        for year in popit_result['standing_in']:
            print("        Constituency in {0}: {1}".format(
                year, popit_result['standing_in'][year]['name']
            ))
        response = ''
        while response.lower() not in ('y', 'n'):
            response = input('Are they the same? (y/Y/n/N) ')
            response = response.lower().strip()
            if response == 'y':
                return True
            elif response == 'n':
                return False

    def handle_person(self, ppc_data, image_filename):
        from candidates.popit import get_search_url
        print("PPC ({party_slug}): {name}".format(**ppc_data).encode('utf-8'))
        # Search PopIt for anyone with the same name. (FIXME: we
        # should make this a bit fuzzier when the PopIt API
        # supports that.)
        person_search_url = get_search_url(
            'persons', '"' + ppc_data['name'] + '"'
        )
        r = requests.get(
            person_search_url
        )
        add_new_person = True
        for result in r.json()['result']:
            # FIXME: With the current code, updating Elasticsearch
            # fails because it rejects the empty string as a null date
            # value. To just get this working, GET the person directly
            # so the information's defintely up to date.
            result = self.api.persons(result['id']).get()['result']
            # We don't need past versions of the person or their
            # memberships, and it's unnecessary verbose to record them
            # with decisions.
            del result['versions']
            del result['memberships']
            popit_person_id = result['id']

            message = "  Considering PopIt person search result {0}"
            print(message.format(popit_person_id))

            added_for_2015 = self.already_added_for_2015(ppc_data, result)
            if added_for_2015 is None:
                add_new_person = False
                print("    already_added_for_2015 returned None, so ignoring")
                print("    !!! CHECK THIS MANUALLY !!!")
                break
            elif added_for_2015:
                # Then just update that person with the possibly
                # updated scraped data:
                add_new_person = False
                print("    matched a 2015 candidate, so updating that")
                self.update_popit_person(popit_person_id, ppc_data, image_filename)
                break
            else:
                # Do we already have a decision about whether this PPC is
                # the same as another from 2010?
                decision = self.already_matched_to_a_person(ppc_data, popit_person_id)
                if decision is None:
                    print("    no previous decision found, so asking")
                    # We have to ask the user for a decision:
                    if self.decision_from_user(ppc_data, result):
                        print("      updating, and recording the decision that they're a match")
                        add_new_person = False
                        self.update_popit_person(popit_person_id, ppc_data, image_filename)
                        record_human_decision(ppc_data, popit_person_id, True)
                        break
                    else:
                        print("      recording the decision that they're not a match")
                        record_human_decision(ppc_data, popit_person_id, False)
                else:
                    # Otherwise we'd previously decided that they're
                    # the same person, so just update that person.
                    print("    there was a previous decision found")
                    if decision:
                        print("      the previous decision was that they're a match, so updating")
                        add_new_person = False
                        self.update_popit_person(popit_person_id, ppc_data, image_filename)
                        break
        if add_new_person:
            new_person_id = self.add_popit_person(ppc_data, image_filename)
            print("  Added them as a new person ({0})".format(new_person_id))

    def handle(self, **options):
        from candidates.election_specific import AREA_DATA

        constituency_lookup = {
            cons_key(k): v for k, v in
            AREA_DATA.areas_by_name[('WMC', '22')].items()
        }

        for party_slug in sorted(os.listdir(ppc_data_directory)):
            json_directory = join(
                ppc_data_directory,
                party_slug
            )
            for leafname in sorted(os.listdir(json_directory)):
                if not leafname.endswith('.json'):
                    continue
                filename = join(json_directory, leafname)
                image = re.sub(r'\.json$', '-cropped.png', filename)
                if not exists(image):
                    image = None
                print('===============================================================')
                print("filename:", filename)
                with open(filename) as f:
                    ppc_data = json.load(f)
                ppc_data['party_slug'] = party_slug
                ppc_data['party_object'] = party_slug_to_popit_party[party_slug]
                ppc_data['constituency_object'] = get_constituency_from_name(
                    ppc_data['constituency'],
                    constituency_lookup
                )
                if options['check']:
                    continue
                self.handle_person(ppc_data, image)
