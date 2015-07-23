from collections import defaultdict
import json
from os.path import abspath, dirname, join, exists

import requests

from django.conf import settings
from django.utils.translation import ugettext as _

data_directory = abspath(join(
    dirname(__file__), '..', 'elections', settings.ELECTION_APP, 'data'
))

def get_mapit_areas(area_type, generation):
    expected_filename = join(
        data_directory,
        'mapit-{area_type}-generation-{generation}.json'.format(
            area_type=area_type,
            generation=generation,
        )
    )
    if exists(expected_filename):
        with open(expected_filename) as f:
            return json.load(f)
    else:
        mapit_url_format = '{base_url}areas/{area_type}?generation={generation}'
        mapit_url = mapit_url_format.format(
            base_url=settings.MAPIT_BASE_URL,
            area_type=area_type,
            generation=generation
        )
        message = "WARNING: failed to find {filename} so loading from MapIt\n"
        message += "This will make start-up slow and less reliable, so consider\n"
        message += "committing a copy of: {url}"
        print message.format(filename=expected_filename, url=mapit_url)
        r = requests.get(mapit_url)
        return r.json()


class BaseMapItData(object):

    """Load MapIt data and make it availale in helpful data structures

    FIXME: check that these are sensible descriptions

    On instantiation, the following attributes are created:

        'areas_by_id', a dictionary that maps from a MapIt ID to full
        area data

        'areas_by_name', a dictionary that maps an area name and typ
        to full area data

        'areas_list_sorted_by_name', a list of all areas of a
        particular type

    """

    def __init__(self):

        self.areas_by_id = {}
        self.areas_by_name = {}
        self.areas_list_sorted_by_name = {}

        for t, election_data in settings.MAPIT_TYPES_GENERATIONS_ELECTIONS.items():
            mapit_type, mapit_generation = t
            self.areas_by_id[t] = get_mapit_areas(mapit_type, mapit_generation)
            for area in self.areas_by_id[t].values():
                self.areas_by_name.setdefault(t, {})
                self.areas_by_name[t][area['name']] = area
            self.areas_list_sorted_by_name[t] = sorted(
                self.areas_by_id[t].items(),
                key=lambda c: c[1]['name']
            )


class BasePartyData(object):

    """You should subclass this in your election application to define the
    election-specific 'party sets'.

    FIXME: check that these are sensible descriptions

    When instantiated, this gives you helpful access to party data in
    two attributes:

    'party_choices' is a dictionary where the keys are the names of
    party sets and the values are lists that can be used as choices in
    a ChoiceField, e.g.:

        {u'Great Britain': [
          ('party:none', ''),
          (u'party:52', u'Conservative Party'),
          (u'joint-party:53-119', u'Labour and Co-operative Party'),
          (u'party:53', u'Labour Party'),
          (u'ynmp-party:2', u'Independent'),
          (u'ynmp-party:12522', u'Speaker seeking re-election')],
         u'Northern Ireland': [
          ('party:none', ''),
          (u'party:51', u'Conservative and Unionist Party'),
          (u'party:434', u'Labour Party of Northern Ireland'),
          (u'ynmp-party:2', u'Independent'),
          (u'ynmp-party:12522', u'Speaker seeking re-election')]}

    'party_id_to_name' is a dictionary that maps party IDs to party
    names, e.g.:

        {u'party:434': u'Labour Party of Northern Ireland',
         u'party:53': u'Labour Party',
         u'joint-party:53-119': u'Labour and Co-operative Party',
         u'party:51': u'Conservative and Unionist Party',
         u'party:52': u'Conservative Party',
         u'ynmp-party:12522': u'Speaker seeking re-election',
         u'ynmp-party:2': u'Independent'}

    """

    def party_data_to_party_set(self, party_data):
        raise NotImplementedError(
            "You should implement party_data_to_party_set in a subclass"
        )

    def sort_parties_in_place(self, parties):
        parties.sort(key=lambda p: p[1].lower())

    def __init__(self):

        self.party_choices = defaultdict(list)
        self.party_id_to_name = {}
        self.all_party_data = []
        with open(join(data_directory, 'all-parties-from-popit.json')) as f:
            for party in json.load(f):
                self.all_party_data.append(party)
                for party_set in self.party_data_to_party_sets(party):
                    self.party_choices[party_set].append(
                        (party['id'], party['name'])
                    )
                    self.party_id_to_name[party['id']] = party['name']
            # Now sort the parties, and an an empty default at the start:
            for parties in self.party_choices.values():
                self.sort_parties_in_place(parties)
                parties.insert(0, ('party:none', ''))


class BaseAreaPostData(object):

    """Instantiate this class to provide mappings between areas and posts

    FIXME: check that these are sensible descriptions

    If you instantiate this class you will get the following attributes:

         'area_ids_and_names_by_post_group', maps a post group to a
         list of all areas of a particular type

         'areas_by_post_id', maps a post ID to all areas associated
         with it
    """

    def area_to_post_group(self, area_data):
        raise NotImplementedError(
            "You should implement area_to_post_group in a subclass"
        )

    def get_post_id(self, election, mapit_type, area_id):
        return settings.ELECTIONS[election]['post_id_format'].format(
            area_id=area_id
        )

    def __init__(self, mapit_data, party_data):
        self.mapit_data = mapit_data
        self.party_data = party_data
        self.areas_by_post_id = {}
        self.area_ids_and_names_by_post_group = {}

        for mapit_tuple, election_tuples in settings.MAPIT_TYPES_GENERATIONS_ELECTIONS.items():
            for election_tuple in election_tuples:
                election, election_data = election_tuple
                mapit_type, mapit_generation = mapit_tuple
                for area in self.mapit_data.areas_by_id[mapit_tuple].values():
                    post_id = self.get_post_id(election, mapit_type, area['id'])
                    if post_id in self.areas_by_post_id:
                        message = _("Found multiple areas for the post ID {post_id}")
                        raise Exception(message.format(post_id=post_id))
                    self.areas_by_post_id[post_id] = area
                for area in mapit_data.areas_by_name[mapit_tuple].values():
                    post_group = self.area_to_post_group(area)
                    self.area_ids_and_names_by_post_group.setdefault(mapit_tuple, defaultdict(list))
                    self.area_ids_and_names_by_post_group[mapit_tuple][post_group].append(
                        (str(area['id']), area['name'])
                    )
                for area_list in self.area_ids_and_names_by_post_group[mapit_tuple].values():
                    area_list.sort(key=lambda c: c[1])
