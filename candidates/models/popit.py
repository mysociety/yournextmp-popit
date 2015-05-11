from copy import deepcopy
from datetime import date, timedelta
import json
import re
import sys
from collections import defaultdict

from slugify import slugify

from django.core.urlresolvers import reverse
import django.dispatch
from django_date_extensions.fields import ApproximateDate
from slumber.exceptions import HttpServerError, HttpClientError

from .auth import (
    get_constituency_lock_from_person_data,
    check_creation_allowed,
    check_update_allowed,
)
from .db import MaxPopItIds

from ..cache import get_person_cached, invalidate_person, invalidate_posts
from ..diffs import get_version_diffs
from ..static_data import MapItData, PartyData

person_added = django.dispatch.Signal(providing_args=["data"])

# This dict stores the simple field names and their null values.  (In
# order not to get mapping type errors from Elasticsearch, dates have
# to be null.)
form_simple_fields = {
    'honorific_prefix': '',
    'name': '',
    'honorific_suffix': '',
    'email': '',
    'birth_date': None,
    'gender': '',
}
preserve_fields = ('identifiers', 'other_names', 'phone', 'death_date')

other_fields_to_proxy = [
    'id', 'image', 'proxy_image', 'versions', 'other_names', 'identifiers'
]

CSV_ROW_FIELDS = [
    'name',
    'id',
    'party',
    'constituency',
    'mapit_id',
    'mapit_url',
    'gss_code',
    'twitter_username',
    'facebook_page_url',
    'party_ppc_page_url',
    'gender',
    'facebook_personal_url',
    'email',
    'homepage_url',
    'wikipedia_url',
    'birth_date',
    'parlparse_id',
    'theyworkforyou_url',
    'honorific_prefix',
    'honorific_suffix',
    'party_id',
    'linkedin_url',
    'elected',
    'image_url',
    'proxy_image_url_template',
    'image_copyright',
    'image_uploading_user',
    'image_uploading_user_notes',
]


form_complex_fields_locations = {
    'wikipedia_url': {
        'sub_array': 'links',
        'info_type_key': 'note',
        'info_value_key': 'url',
        'info_type': 'wikipedia',
    },
    'linkedin_url': {
        'sub_array': 'links',
        'info_type_key': 'note',
        'info_value_key': 'url',
        'info_type': 'linkedin',
    },
    'homepage_url': {
        'sub_array': 'links',
        'info_type_key': 'note',
        'info_value_key': 'url',
        'info_type': 'homepage',
    },
    'twitter_username': {
        'sub_array': 'contact_details',
        'info_type_key': 'type',
        'info_value_key': 'value',
        'info_type': 'twitter',
    },
    'facebook_personal_url': {
        'sub_array': 'links',
        'info_type_key': 'note',
        'info_value_key': 'url',
        'info_type': 'facebook personal',
    },
    'facebook_page_url': {
        'sub_array': 'links',
        'info_type_key': 'note',
        'info_value_key': 'url',
        'info_type': 'facebook page',
    },
    'party_ppc_page_url': {
        'sub_array': 'links',
        'info_type_key': 'note',
        'info_value_key': 'url',
        'info_type': 'party PPC page',
    }
}

# FIXME: https://github.com/mysociety/yournextmp-popit/issues/354

election_date_2005 = date(2005, 5, 5)
election_date_2010 = date(2010, 5, 6)
election_date_2015 = date(2015, 5, 7)

election_to_election_date = {
    '2005': election_date_2005,
    '2010': election_date_2010,
    '2015': election_date_2015,
}

# end of FIXME

all_form_fields = form_simple_fields.keys() + \
    form_complex_fields_locations.keys()

candidate_list_name_re = re.compile(r'^Candidates for (.*) in (\d+)$')

def parse_approximate_date(s):
    """Take a partial ISO 8601 date, and return an ApproximateDate for it

    >>> ad = parse_approximate_date('2014-02-17')
    >>> type(ad)
    <class 'django_date_extensions.fields.ApproximateDate'>
    >>> ad
    2014-02-17
    >>> parse_approximate_date('2014-02')
    2014-02-00
    >>> parse_approximate_date('2014')
    2014-00-00
    >>> parse_approximate_date('future')
    future
    """

    for regexp in [
        r'^(\d{4})-(\d{2})-(\d{2})$',
        r'^(\d{4})-(\d{2})$',
        r'^(\d{4})$'
    ]:
        m = re.search(regexp, s)
        if m:
            return ApproximateDate(*(int(g, 10) for g in m.groups()))
    if s == 'future':
        return ApproximateDate(future=True)
    raise Exception, "Couldn't parse '{0}' as an ApproximateDate".format(s)

def get_area_from_post_id(post_id, mapit_url_key='id'):
    "Get a MapIt area ID from a candidate list organization's PopIt data"

    mapit_data = MapItData.constituencies_2010.get(post_id)
    if mapit_data is None:
        message = "Couldn't find the constituency with Post and MapIt Area ID: '{0}'"
        raise Exception(message.format(post_id))
    url_format = 'http://mapit.mysociety.org/area/{0}'
    return {
        'name': mapit_data['name'],
        'post_id': post_id,
        mapit_url_key: url_format.format(post_id),
    }

def complete_partial_date(iso_8601_date_partial, start=True):
    """If we have a partial date string, complete it for range comparisons

    If 'start' is true, then fill in month and date parts with values
    that are as early as possible; if it's false make them as late as
    possible.  For example:

    >>> complete_partial_date('2001', True)
    '2001-01-01'
    >>> complete_partial_date('2001', False)
    '2001-12-31'
    >>> complete_partial_date('1970-04', True)
    '1970-04-01'
    >>> complete_partial_date('1970-04', False)
    '1970-04-31'
    >>> complete_partial_date('2014-09-21', True)
    '2014-09-21'
    >>> complete_partial_date('2014-09-21', False)
    '2014-09-21'

    """

    if start:
        default_month = '01'
        default_day = '01'
    else:
        default_month = '12'
        default_day = '31'
    if re.search(r'^\d{4}$', iso_8601_date_partial):
        return '{0}-{1}-{2}'.format(iso_8601_date_partial, default_month, default_day)
    elif re.search(r'^\d{4}-\d{2}$', iso_8601_date_partial):
        return '{0}-{1}'.format(iso_8601_date_partial, default_day)
    elif re.search(r'^\d{4}-\d{2}-\d{2}$', iso_8601_date_partial):
        return iso_8601_date_partial
    else:
        raise Exception, "Unknown partial ISO 8601 data format: {0}".format(iso_8601_date_partial)

def membership_covers_date(membership, date):
    """See if the dates in a membership cover a particular date

    For example:

    >>> membership_covers_date({
    ...     'start_date': '2010',
    ...     'end_date': '2015-01-01',
    ... }, date(2010, 5, 6))
    True

    >>> membership_covers_date({
    ...     'start_date': '2010-08',
    ...     'end_date': '2015',
    ... }, date(2010, 5, 6))
    False

    If a start date is missing, assume it's 'since forever' and if an
    end date is missing, assume it's 'until forever':

    >>> membership_covers_date({'end_date': '2014'}, date(2010, 5, 6))
    True
    >>> membership_covers_date({'end_date': '2010-03'}, date(2010, 5, 6))
    False
    >>> membership_covers_date({'start_date': '2014'}, date(2010, 5, 6))
    False
    >>> membership_covers_date({'start_date': '1976'}, date(2010, 5, 6))
    True
    >>> membership_covers_date({}, date(2010, 5, 6))
    True
    """

    start_date = membership.get('start_date')
    if not start_date:
        start_date = '0001-01-01'
    end_date = membership.get('end_date')
    if not end_date:
        end_date = '9999-12-31'
    start_date = complete_partial_date(start_date)
    end_date = complete_partial_date(end_date)
    return start_date <= str(date) and end_date >= str(date)

def is_party_membership(membership):
    """This predicate works whether the organization is embedded or not"""

    role = membership.get('role', 'Member').lower()
    if role != 'member':
        return False
    organization_id = membership['organization_id']
    try:
        classification = organization_id.get('classification', '')
        return classification.lower() == 'party'
    except AttributeError:
        # If organization_id is actually just an ID, guess from the
        # ID's format:
        party_id_match = re.search(
            r'^(party|ynmp-party|joint-party):',
            organization_id
        )
        return bool(party_id_match)

def is_candidacy_membership(membership):
    role = membership.get('role', '').lower()
    return (role == 'candidate')

def is_mp_membership(membership):
    role = membership.get('role', 'Member').lower()
    if role != 'member':
        return False
    return membership.get('organization_id') == 'commons'

def is_standing_in_membership(membership):
    return is_candidacy_membership(membership) or is_mp_membership(membership)

# FIXME: really this should be a method on a PopIt base class, so it's
# available for both people and organizations.
def get_identifier(scheme, popit_object):
    result = None
    for identifier in popit_object.get('identifiers', []):
        if identifier['scheme'] == scheme:
            result = identifier['identifier']
            break
    return result

def get_mapit_id_from_mapit_url(mapit_url):
    m = re.search(r'http://mapit.mysociety.org/area/(\d+)', mapit_url)
    if not m:
        raise Exception("Failed to parse the MapIt URL: {0}".format(mapit_url))
    return m.group(1)

def create_person_with_id_retries(api, data):
    id_to_try = MaxPopItIds.get_max_persons_id() + 1
    id_str = str(id_to_try)
    while True:
        try:
            data['id'] = id_str
            data['versions'][0]['data']['id'] = id_str
            result = api.persons.post(data)
            MaxPopItIds.update_max_persons_id(id_to_try)
            break
        except HttpServerError as hse:
            # Sometimes the ID that we try will be taken already, so
            # detect that case, otherwise just reraise the exception.
            error = json.loads(hse.content)
            if error.get('error', {}).get('code') == 11000:
                id_to_try += 1
                continue
            else:
                raise
    return result

def election_year_to_party_dates(election_year):
    if str(election_year) == '2010':
        return {
            'start_date': str(election_date_2005 + timedelta(days=1)),
            'end_date': str(election_date_2010),
        }
    elif str(election_year) == '2015':
        return {
            'start_date': str(election_date_2010 + timedelta(days=1)),
            'end_date': '9999-12-31',
        }
    else:
        raise Exception('Unknown election year: {0}'.format(election_year))

def extract_constituency_name(candidate_list_organization):
    """Return the constituency name from a candidate list organization

    >>> extract_constituency_name({
    ...     'name': 'Candidates for Altrincham and Sale West in 2015'
    ... })
    'Altrincham and Sale West'
    >>> constituency_name = extract_constituency_name({
    ...     'name': 'Another Organization'
    ... })
    >>> print constituency_name
    None
    """
    m = candidate_list_name_re.search(
        candidate_list_organization['name']
    )
    if m:
        return m.group(1)
    return None

def get_constituency_name_from_mapit_id(mapit_id):
    constituency_data = MapItData.constituencies_2010.get(str(mapit_id))
    if constituency_data:
        return constituency_data['name']
    return None

def reduced_organization_data(organization):
    return {
        'id': organization['id'],
        'name': organization['name'],
    }

def get_value_from_location(location, person_data):
    for info in person_data.get(location['sub_array'], []):
        if info[location['info_type_key']] == location['info_type']:
            return info.get(location['info_value_key'], '')
    return ''

def unembed_membership(membership):
    """Remove any embeds from a membership to make it ready for posting

    >>> m = unembed_membership({
    ...     'foo': 'bar',
    ...     'person_id': '123',
    ...     'post_id': '456',
    ...     'organization_id': '789',
    ... })
    >>> print json.dumps(m, indent=4, sort_keys=True) # doctest: +NORMALIZE_WHITESPACE
    {
        "foo": "bar",
        "organization_id": "789",
        "person_id": "123",
        "post_id": "456"
    }
    >>> m = unembed_membership({
    ...     'foo': 'bar',
    ...     'person_id': {
    ...        'id': '123',
    ...        'name': 'Fozzie Bear',
    ...     },
    ...     'post_id': {
    ...         'id': '456',
    ...         'name': 'Member of Parliament for Manhattan',
    ...     },
    ...     'organization_id': {
    ...         'id': '789',
    ...         'name': 'The Muppet Show',
    ...     },
    ... })
    >>> print json.dumps(m, indent=4, sort_keys=True) # doctest: +NORMALIZE_WHITESPACE
    {
        "foo": "bar",
        "organization_id": "789",
        "person_id": "123",
        "post_id": "456"
    }
    >>> m = unembed_membership({
    ...     'foo': 'bar',
    ...     'person_id': {
    ...        'id': '123',
    ...        'name': 'Fozzie Bear',
    ...     },
    ...     'organization_id': {
    ...         'id': '789',
    ...         'name': 'The Muppet Show',
    ...     },
    ... })
    >>> print json.dumps(m, indent=4, sort_keys=True) # doctest: +NORMALIZE_WHITESPACE
    {
        "foo": "bar",
        "organization_id": "789",
        "person_id": "123"
    }

    Also, sometimes some rogue fields have crept into memberships, so
    remove them or they may cause the POST to fail:

    >>> m = unembed_membership({
    ...     'foo': 'bar',
    ...     'person_id': '123',
    ...     'organization_id': '789',
    ...     'area': {'name': ''},
    ...     'images': [],
    ...     'contact_details': [],
    ...     'links': [],
    ...     'url': 'http://yournextmp.popit.mysociety.org/api/v0.1/memberships/blahblah',
    ...     'html_url': 'http://yournextmp.popit.mysociety.org/memberships/blahblah',
    ... })
    >>> print json.dumps(m, indent=4, sort_keys=True) # doctest: +NORMALIZE_WHITESPACE
    {
        "foo": "bar",
        "organization_id": "789",
        "person_id": "123"
    }
    """
    m = deepcopy(membership)
    for id_field in ('organization_id', 'person_id', 'post_id'):
        try:
            if id_field in m:
                m[id_field] = m[id_field].get('id')
        except AttributeError:
            pass
    for bad_field in (
            'area', 'images', 'contact_details', 'links', 'url', 'html_url'
    ):
        m.pop(bad_field, None)
    return m


class StalePopItData(Exception):
    pass


# FIXME: a hacky workaround to make sure that we don't set
# dates to an empty string, which will stop the PopIt record
# being indexed by Elasticsearch.
def fix_dates(data):
    for key in ('birth_date', 'death_date'):
        if key in data and not data[key]:
            data[key] = None
    for other_name in data.get('other_names', []):
        for key in ('start_date', 'end_date'):
            if key in other_name and not other_name[key]:
                other_name[key] = None


class PopItPerson(object):

    def __init__(self, popit_data=None):
        self.popit_data = popit_data or {}
        self.posts_to_invalidate = set()
        self.store_posts_for_invalidation()
        # Our overridden __setattr__ will only be used after
        # self._initialized is set to True.
        self._initialized = True

    def __eq__(self, other):
        return self.id == other.id

    def __hash__(self):
        return hash(self.id)

    @classmethod
    def create_from_popit(cls, api, popit_person_id):
        popit_data = get_person_cached(api, popit_person_id)['result']
        new_person = cls(popit_data=popit_data)
        return new_person

    @classmethod
    def create_from_reduced_json(cls, reduced_json):
        new_person = PopItPerson()
        new_person.update_from_reduced_json(reduced_json)
        return new_person

    def update_from_reduced_json(self, reduced_json):
        '''Convert our representation to person data can that be sent to PopIt

        Our representation is a flatter one, which corresponds in part to
        the fields in the "edit person" forms; in addition there are the
        'standing_in' and 'party_memberships' objects that are only used
        for creating memberships (i.e. not "person_data" in the sense of
        this method. There are also some fields that we should just
        preserve in this transformation, like 'identifiers'.'''

        new_popit_data = {}
        # First deal with fields that simply map to top level fields in
        # Popolo.
        for field_name, null_value in form_simple_fields.items():
            if reduced_json.get(field_name):
                new_popit_data[field_name] = unicode(reduced_json[field_name])
            else:
                # Otherwise, set the field to its null value
                new_popit_data[field_name] = null_value
        new_popit_data['id'] = reduced_json.get('id')
        for field_name in preserve_fields:
            if field_name in reduced_json:
                new_popit_data[field_name] = reduced_json[field_name]
        # These are fields which are represented by values in a sub-object
        # in Popolo's JSON serialization:
        for field_name, location in form_complex_fields_locations.items():
            new_value = reduced_json.get(field_name, '')
            if new_value:
                update_values_in_sub_array(new_popit_data, location, new_value)
        new_popit_data['memberships'] = []
        # Update popit_data from the new popit_data; this makes sure,
        # for example, that the versions array is preserved
        self.popit_data.update(new_popit_data)
        self.standing_in = reduced_json.get('standing_in', {})
        self.party_memberships = reduced_json.get('party_memberships', {})
        self.store_posts_for_invalidation()

    @classmethod
    def create_from_dict(cls, person_dict):
        new_person = cls(popit_data=person_dict)
        return new_person

    # Make various data from PopIt available as properties on this
    # object:
    def __getattr__(self, name):
        fields_to_proxy = form_simple_fields.keys() + other_fields_to_proxy
        if name in fields_to_proxy:
            return self.popit_data.get(name)
        elif name in form_complex_fields_locations:
            return get_value_from_location(
                form_complex_fields_locations[name],
                self.popit_data
            )
        elif name in self.__dict__:
            return super(PopItPerson, self).__getattr__(name)
        else:
            raise AttributeError(
                "'PopItPerson' has no attribute '{0}'".format(name)
            )

    def __setattr__(self, name, value):
        if not self.__dict__.get('_initialized'):
            super(PopItPerson, self).__setattr__(name, value)
        else:
            if (name in form_simple_fields) or (name in other_fields_to_proxy):
                self.popit_data[name] = value
            elif name in form_complex_fields_locations:
                update_values_in_sub_array(
                    self.popit_data,
                    form_complex_fields_locations[name],
                    value
                )
            else:
                super(PopItPerson, self).__setattr__(name, value)

    def get_slug(self):
        return slugify(self.name)

    @property
    def last_name(self):
        """Return the last name, split on whitespace

        >>> p = PopItPerson.create_from_dict({'name': 'Joe H Bloggs'})
        >>> p.last_name
        'Bloggs'

        We shouldn't have an empty string as the name, but deal with
        that anyway:

        >>> p = PopItPerson.create_from_dict({'name': ''})
        >>> p.last_name
        ''
        """

        split_name = self.name.split()
        if split_name:
            return split_name[-1]
        else:
            return ''

    @property
    def images(self):
        return self.popit_data.get('images', [])

    @property
    def version_diffs(self):
        return get_version_diffs(self.popit_data['versions'])

    def get_second_last_version(self):
        if len(self.versions) < 2:
            raise Exception, "There was no previous version of this person"
        return PopItPerson.create_from_reduced_json(
            self.versions[1]['data']
        )

    def constituency_or_party_changes_allowed(self, user, api):
        return get_constituency_lock_from_person_data(
            user, api, self.popit_data
        )

    def name_with_honorifics(self):
        name_parts = []
        pre = self.popit_data.get('honorific_prefix')
        post = self.popit_data.get('honorific_suffix')
        if pre:
            name_parts.append(pre)
        name_parts.append(self.popit_data.get('name', ''))
        if post:
            name_parts.append(post)
        return ' '.join(name_parts)

    @property
    def parties(self):
        results = {}
        for membership in self.popit_data['memberships']:
            organization = membership.get('organization_id')
            if not organization:
                continue
            if organization['classification'] != "Party":
                continue

            for identifier in organization['identifiers']:
                if identifier['scheme'] == "electoral-commission":
                    organization['electoral_commission_id'] =\
                         identifier['identifier']

            if membership_covers_date(membership, election_date_2010):
                results['2010'] = organization
            if membership_covers_date(membership, election_date_2015):
                results['2015'] = organization
        return results

    @property
    def standing_in(self):
        return self.popit_data.get('standing_in', {})

    @standing_in.setter
    def standing_in(self, v):
        # Preserve all the memberships that aren't candidate
        # memberships or actual members of the post.
        memberships = [
            m for m in
            self.popit_data.get('memberships', [])
            if not is_standing_in_membership(m)
        ]
        # And now add the new memberships from the value that's being
        # set:
        for election_year, constituency in v.items():
            if constituency:
                # i.e. we know that this isn't an indication that the
                # person isn't standing...
                # Create the candidate list membership:
                membership = election_year_to_party_dates(election_year)
                membership['person_id'] = self.id
                membership['post_id'] = constituency['post_id']
                membership['role'] = "Candidate"
                memberships.append(membership)
                if constituency.get('elected'):
                    day_after = election_to_election_date[election_year] + \
                        timedelta(days=1)
                    memberships.append({
                        'start_date': str(day_after),
                        'end_date': '9999-12-31',
                        'person_id': self.id,
                        'post_id': constituency['post_id'],
                        # FIXME: https://github.com/mysociety/yournextmp-popit/issues/354
                        'organization_id': 'commons',
                    })

        self.popit_data['memberships'] = memberships
        self.popit_data['standing_in'] = v

    @property
    def party_memberships(self):
        return self.popit_data.get('party_memberships', {})

    @party_memberships.setter
    def party_memberships(self, v):
        # Find all memberships that aren't party memberships:
        memberships = [
            m for m in
            self.popit_data['memberships']
            if not is_party_membership(m)
        ]
        # And now add the new memberships from the value that's being
        # set:
        for election_year, party in v.items():
            membership = election_year_to_party_dates(election_year)
            membership['person_id'] = self.id
            membership['organization_id'] = party['id']
            memberships.append(membership)
        self.popit_data['memberships'] = memberships
        self.popit_data['party_memberships'] = v

    def get_associated_posts(self):
        post_ids = set()
        if not self.standing_in:
            return post_ids
        for year, data in self.standing_in.items():
            if data:
                post_id = data.get('post_id')
                if post_id:
                    post_ids.add(post_id)
        return post_ids

    def invalidate_cache_entries(self):
        invalidate_posts(self.posts_to_invalidate)
        self.posts_to_invalidate = set()
        invalidate_person(self.id)

    def store_posts_for_invalidation(self):
        self.posts_to_invalidate.update(self.get_associated_posts())

    @property
    def known_status_in_2015(self):
        standing_in = self.popit_data.get('standing_in', {}) or {}
        return '2015' in standing_in

    @property
    def not_standing_in_2015(self):
        # If there's a standing_in element present, its '2015' value
        # is set to None, then we someone has marked that person as
        # not standing...
        standing_in = self.popit_data.get('standing_in', {}) or {}
        return ('2015' in standing_in) and standing_in['2015'] == None

    def delete_memberships(self, api):
        person_from_popit = api.persons(self.id).get(embed='membership')
        for membership in person_from_popit['result']['memberships']:
            api.memberships(membership['id']).delete()

    def create_memberships(self, api):
        for m in self.popit_data['memberships']:
            # The memberships might still be here from when the person
            # was populated with the embed parameter, so make sure t
            safe_to_post = unembed_membership(m)
            safe_to_post.pop('id', None)
            try:
                api.memberships.post(safe_to_post)
            except HttpClientError as hce:
                # We've been seeing some errors in creating
                # memberships, but with no useful error, so dump the
                # attempted call and the error content here:
                print >> sys.stderr, u'Error with POST of membership:'
                print >> sys.stderr, repr(safe_to_post)
                print >> sys.stderr, hce.content
                raise

    def get_identifier(self, scheme):
        return get_identifier(scheme, self.popit_data)

    def set_identifier(self, scheme, value):
        update_values_in_sub_array(
            self.popit_data,
            {'sub_array': 'identifiers',
             'info_type_key': 'scheme',
             'info_value_key': 'identifier',
             'info_type': scheme},
            value
        )

    def as_dict(self, year='2015'):
        """
        Returns a list in the order of CSV_ROW_FIELDS, for ease of
        converting PopItPerson objects in to CSV representations.
        """

        person_data = defaultdict(str)
        person_data.update(self.popit_data['versions'][0]['data'])

        theyworkforyou_url = None
        parlparse_id = get_identifier('uk.org.publicwhip', self.popit_data)
        if parlparse_id:
            m = re.search(r'^uk.org.publicwhip/person/(\d+)$', parlparse_id)
            if not m:
                message = "Malformed parlparse ID found {0}"
                raise Exception, message.format(parlparse_id)
            parlparse_person_id = m.group(1)
            theyworkforyou_url = 'http://www.theyworkforyou.com/mp/{0}'.format(
                parlparse_person_id
            )
        elected = self.get_elected(year)
        elected_for_csv = ''
        if elected is not None:
            elected_for_csv = str(elected)
        image = self.popit_data.get('image', '') or ''
        proxy_image_url_template = ''
        image_copyright = ''
        image_uploading_user = ''
        image_uploading_user_notes = ''
        if image:
            proxy_image_url_template = \
                self.popit_data['proxy_image'] + '/{width}/{height}.{extension}'
            image_data = self.popit_data['images'][0]
            image_copyright = image_data.get('moderator_why_allowed', '')
            image_uploading_user = image_data.get('uploaded_by_user', '')
            image_uploading_user_notes = \
                image_data.get('user_justification_for_use', '')
        row = {
            'honorific_prefix': self.popit_data.get('honorific_prefix', ''),
            'name': self.name,
            'honorific_suffix': self.popit_data.get('honorific_suffix', ''),
            'id': self.id,
            'party': person_data['party_memberships'][year]['name'],
            'constituency': self.standing_in[year]['name'],
            'mapit_url': self.standing_in[year]['mapit_url'],
            'mapit_id': self.standing_in[year]['post_id'],
            'gss_code': MapItData.constituencies_2010[
                self.standing_in[year]['post_id']]['codes']['gss'],
            'twitter_username': person_data['twitter_username'],
            'facebook_page_url': person_data['facebook_page_url'],
            'linkedin_url': person_data['linkedin_url'],
            'party_ppc_page_url': person_data['party_ppc_page_url'],
            'gender': person_data['gender'],
            'facebook_personal_url': person_data['facebook_personal_url'],
            'email': person_data['email'],
            'homepage_url': person_data['homepage_url'],
            'wikipedia_url': person_data['wikipedia_url'],
            'birth_date': person_data['birth_date'],
            'parlparse_id': parlparse_id,
            'theyworkforyou_url': theyworkforyou_url,
            'party_id': self.parties[year].get('electoral_commission_id'),
            'elected': elected_for_csv,
            'image_url': self.popit_data.get('image', ''),
            'proxy_image_url_template': proxy_image_url_template,
            'image_copyright': image_copyright,
            'image_uploading_user': image_uploading_user,
            'image_uploading_user_notes': image_uploading_user_notes,
        }

        return row

    def as_reduced_json(self):
        """Get the representation of this person used in 'versions'

        All actions taken by the front-end can be seen as
        person-centric.  We use an intermediate representation (a
        Python dictionary) of what that person and their membership
        should look like - this is the representation of them stored
        in the 'versions' array, which has enough information to
        completely recreate the person at that version.

        The dictionary represents everything we're interested in about
        a candidate's status.  It may have the following fields, which
        are straighforward and set to the empty string if unknown,
        unless they're a date field, in which case they should be null.

          'id'
          'full_name'
          'email'
          'birth_date'
          'wikipedia_url'
          'linkedin_url'
          'homepage_url'
          'twitter_username'

        It should also have a 'party_memberships' member which is set
        to a dictionary.  If someone was known to be standing for the
        Conservatives in 2010 and UKIP in 2015, this would be:

          'party_memberships': {
            '2010': {
              'name': 'Conservative Party',
              'id': 'party:52',
            '2015': {
              'name': 'UK Independence Party - UKIP',
              'id': 'party:85',
            }
          }

        If someone is standing in 2015 for Labour, but wasn't standing
        in 2010, this should be:

          'party_memberships': {
            '2015': {
              'name': 'Labour Party',
              'id': 'party:53',
          }

        Finally, there is a 'standing_in' member which indicates if a
        person if known to be standing in 2010 or 2015:

        If someone was standing in 2010 in South Cambridgeshire, but
        nothing is known about 2015, this would be:

          'standing_in': {
            '2010': {
              'name': 'South Cambridgeshire',
              'post_id': '65922',
              'mapit_url': 'http://mapit.mysociety.org/area/65922',
            }
          }

        If someone was standing in 2010 in Aberdeen South but is known
        not to be standing in 2015, this would be:

          'standing_in': {
            '2010': {
               'name': 'Aberdeen South',
               'post_id': '14399',
               'mapit_url': 'http://mapit.mysociety.org/area/14399',
            }
            '2015': None,
          }

        If someone was standing in Edinburgh East in 2010, but nothing
        is known about whether they're standing in 2015, this would
        be:

          'standing_in': {
            '2010': {
               'name': 'Aberdeen South',
               'post_id': '14399',
               'mapit_url': 'http://mapit.mysociety.org/area/14399',
            },
          }

        Or if someone is known to be standing in Edinburgh East in
        2010 and then is thought to be standing in Edinburgh North and
        Leith in 2015, this would be:

          'standing_in': {
            '2010': {
               'name': 'Edinburgh East',
               'post_id': '14419',
               'mapit_url': 'http://mapit.mysociety.org/area/14419',
            },
            '2015': {
               'name': 'Edinburgh North and Leith',
               'post_id': '14420',
               'mapit_url': 'http://mapit.mysociety.org/area/14420',
            },
          }

        """
        result = {'id': self.id}
        for field, null_value in form_simple_fields.items():
            result[field] = self.popit_data.get(field) or null_value
        for field, location in form_complex_fields_locations.items():
            result[field] = get_value_from_location(location, self.popit_data)

        result['standing_in'] = self.popit_data['standing_in']
        result['party_memberships'] = self.popit_data['party_memberships']
        result['image'] = self.popit_data.get('image')
        result['proxy_image'] = self.popit_data.get('proxy_image')
        result['other_names'] = self.popit_data.get('other_names', [])
        result['identifiers'] = self.popit_data.get('identifiers', [])
        return result

    @property
    def dob_as_approximate_date(self):
        return parse_approximate_date(self.birth_date)

    def dob_as_date(self):
        approx = self.dob_as_approximate_date
        return date(approx.year, approx.month, approx.day)

    @property
    def age(self):
        """Return a string representing the person's age"""

        dob = self.dob_as_approximate_date
        if not dob:
            return None
        today = date.today()
        approx_age = today.year - dob.year
        if dob.month == 0 and dob.day == 0:
            min_age = approx_age - 1
            max_age = approx_age
        elif dob.day == 0:
            min_age = approx_age - 1
            max_age = approx_age
            if today.month < dob.month:
                max_age = min_age
            elif today.month > dob.month:
                min_age = max_age
        else:
            # There's a complete date:
            dob_as_date = self.dob_as_date()
            try:
                today_in_birth_year = date(dob.year, today.month, today.day)
            except ValueError:
                # It must have been February 29th
                today_in_birth_year = date(dob.year, 3, 1)
            if today_in_birth_year > dob_as_date:
                min_age = max_age = today.year - dob.year
            else:
                min_age = max_age = (today.year - dob.year) -1
        if min_age == max_age:
            # We know their exact age:
            return str(min_age)
        return "{0} or {1}".format(min_age, max_age)

    def get_initial_form_data(self):
        """For use to get the initial data for a form for editing the person"""

        initial_data = {}
        for field_name in all_form_fields:
            initial_data[field_name] = getattr(self, field_name)
        # If there's data from 2010, set that in initial data to
        # provide useful defaults ...
        if '2010' in self.standing_in:
            area_id_2010 = self.standing_in['2010']['post_id']
            initial_data['constituency'] = area_id_2010
            country_name =  MapItData.constituencies_2010.get(area_id_2010)['country_name']
            key = 'party_ni' if country_name == 'Northern Ireland' else 'party_gb'
            initial_data[key] = self.party_memberships['2010']['id']
        # ... but if there's data for 2015, it'll overwrite any
        # defaults from 2010:
        if '2015' in self.standing_in:
            standing_in_2015 = self.standing_in.get('2015')
            if standing_in_2015 is None:
                initial_data['standing'] = 'not-standing'
            elif standing_in_2015:
                initial_data['standing'] = 'standing'
                # First make sure the constituency select box has the right value:
                cons_data_2015 = self.standing_in.get('2015', {})
                mapit_url = cons_data_2015.get('mapit_url')
                if mapit_url:
                    area_id = get_mapit_id_from_mapit_url(mapit_url)
                    initial_data['constituency'] = area_id
                    # Get the 2015 party ID:
                    party_data_2015 = self.party_memberships.get('2015', {})
                    party_id = party_data_2015.get('id', '')
                    # Get the right country based on that constituency:
                    country = MapItData.constituencies_2010.get(area_id)['country_name']
                    if country == 'Northern Ireland':
                        initial_data['party_ni'] = party_id
                    else:
                        initial_data['party_gb'] = party_id
            else:
                message = "Unexpected 'standing_in' value {0}"
                raise Exception(message.format(standing_in_2015))
        else:
            initial_data['standing'] = 'not-sure'
            # TODO: If we don't know someone to be standing, assume they are
            # still in the same party as they were in 2010
        return initial_data

    @property
    def last_party(self):
        party = None
        sorted_memberships = sorted(
            self.popit_data['memberships'],
            key=lambda m: m.get('end_date', '')
        )
        for m in sorted_memberships:
            if is_party_membership(m):
                party = m['organization_id']
        return party

    @property
    def last_cons(self):
        result = None
        for year in ('2010', '2015'):
            cons = self.popit_data['standing_in'].get(year)
            if cons:
                result = (year, cons)
        return result

    def record_version(self, change_metadata):
        new_version = change_metadata.copy()
        new_version['data'] = self.as_reduced_json()
        self.popit_data.setdefault('versions', [])
        self.popit_data['versions'].insert(0, new_version)

    def get_absolute_url(self, request=None):
        path = reverse(
            'person-view',
            kwargs={
                'person_id': self.id,
                'ignored_slug': self.get_slug(),
            }
        )
        if request is None:
            return path
        return request.build_absolute_uri(path)

    def create_new_person_in_popit(self, api):
        popit_data_for_put = deepcopy(self.popit_data)
        # Memberships are created separately, until we switch the API
        # version to one that allows you to PUT embedded memberships
        # (see issue [to find once I'm off a train])
        popit_data_for_put.pop('memberships', None)
        person_result = create_person_with_id_retries(
            api,
            popit_data_for_put
        )
        new_person_id = person_result['result']['id']
        self.popit_data['id'] = new_person_id
        for m in self.popit_data['memberships']:
            m['person_id'] = new_person_id
        person_added.send(sender=PopItPerson, data=self.popit_data)

    def update_person_in_popit(self, api):
        # FIXME: this is a rather horrid workaround for:
        # https://github.com/mysociety/popit-api/issues/95
        popit_data_for_purging = deepcopy(self.popit_data)
        popit_data_for_purging['standing_in'] = None
        popit_data_for_purging['party_memberships'] = None
        popit_data_for_purging['links'] = []
        popit_data_for_purging.pop('memberships', None)
        popit_data_for_purging['contact_details'] = []
        popit_data_for_purging['other_names'] = []
        api.persons(self.id).put(popit_data_for_purging)
        # end of FIXME <-- remove when #95 is fixed
        popit_data_for_put = deepcopy(self.popit_data)
        # Memberships are created separately, until we switch the API
        # version to one that allows you to PUT embedded memberships
        # (see issue [to find once I'm off a train])
        popit_data_for_put.pop('memberships', None)
        api.persons(self.id).put(popit_data_for_put)
        self.delete_memberships(api)

    def save_to_popit(self, api, user=None):
        fix_dates(self.popit_data)
        if self.id:
            previous_version = self.get_second_last_version()
            if user is not None:
                check_update_allowed(
                    user,
                    api,
                    previous_version.popit_data,
                    self.popit_data
                )
            self.update_person_in_popit(api)
        else:
            if user is not None:
                check_creation_allowed(user, api, self.popit_data)
            self.create_new_person_in_popit(api)
        self.create_memberships(api)
        self.invalidate_cache_entries()
        return self.id

    def update_from_form(self, form):
        form_data = form.cleaned_data.copy()
        # The date is returned as a datetime.date, so if that's set, turn
        # it into a string:
        birth_date_date = form_data['birth_date']
        if birth_date_date:
            form_data['birth_date'] = repr(birth_date_date).replace("-00-00", "")
        else:
            form_data['birth_date'] = None
        area_id = form_data.get('constituency')
        # Take either the GB or NI party select, and set it on 'party':
        if area_id:
            country_name =  MapItData.constituencies_2010.get(area_id)['country_name']
            key = 'party_ni' if country_name == 'Northern Ireland' else 'party_gb'
            form_data['party'] = form_data[key]
        else:
            form_data['party'] = None
        del form_data['party_gb']
        del form_data['party_ni']

        # Extract some fields that we will deal with separately:
        standing = form_data.pop('standing', 'standing')
        constituency_2015_mapit_id = form_data.pop('constituency')
        party_2015 = form_data.pop('party')

        new_standing_in = deepcopy(self.standing_in)
        new_party_memberships = deepcopy(self.party_memberships)

        if standing == 'standing':
            constituency_name = get_constituency_name_from_mapit_id(
                constituency_2015_mapit_id
            )
            if not constituency_name:
                message = "Failed to find a constituency with MapIt ID {}"
                raise Exception(message.format(constituency_2015_mapit_id))
            new_standing_in['2015'] = \
                get_area_from_post_id(constituency_2015_mapit_id, mapit_url_key='mapit_url')
            # FIXME: stupid hack to preserve elected status after the election:
            old_standing_in_2015 = self.standing_in.get('2015', {})
            if 'elected' in old_standing_in_2015:
                new_standing_in['2015']['elected'] = old_standing_in_2015['elected']
            new_party_memberships['2015'] = {
                'name': PartyData.party_id_to_name[party_2015],
                'id': party_2015,
            }
        elif standing == 'not-standing':
            # If the person is not standing in 2015, record that
            # they're not and remove the party membership for 2015:
            new_standing_in['2015'] = None
            if '2015' in new_party_memberships:
                del new_party_memberships['2015']
        elif standing == 'not-sure':
            # If the update specifies that we're not sure if they're
            # standing in 2015, then remove the standing_in and
            # party_memberships entries for that year:
            new_standing_in.pop('2015', None)
            new_party_memberships.pop('2015', None)

        self.standing_in = new_standing_in
        self.party_memberships = new_party_memberships

        # Now update the other fields:
        settable_fields = form_simple_fields.keys() + \
            form_complex_fields_locations.keys()
        for field in settable_fields:
            setattr(self, field, form_data[field])

    def set_elected(self, was_elected, year="2015"):
        standing_in = self.standing_in
        if not standing_in:
            message = "Can't set_elected of a candidate with no standing_in"
            raise Exception, message
        if not standing_in.get(year):
            message = "No standing_in information for {0}".format(year)
        if was_elected is None:
            del standing_in[year]['elected']
        else:
            standing_in[year]['elected'] = was_elected
        self.standing_in = standing_in

    def get_elected(self, year="2015"):
        standing_in = self.popit_data.get('standing_in') or {}
        if year not in standing_in:
            return None
        year_data = standing_in.get(year, {})
        if not year_data:
            return None
        return year_data.get('elected')

def update_values_in_sub_array(data, location, new_value):
    """Ensure that only a particular value is present in a sub-dict

    This is useful for replacing values nested in sub-objects of JSON
    data.  This is best demonstrated with an example: if we wanted to
    change the homepage URL in a person record, you could do it like
    this:

    >>> person_data = {
    ...     'id': "john-doe",
    ...     'name': "John Doe",
    ...     'email': "john-doe@example.org",
    ...     'links': [
    ...         {
    ...             'note': "wikipedia",
    ...             'url': "http://en.wikipedia.org/wiki/John_Doe"
    ...         },
    ...         {
    ...             'note': "instagram",
    ...             'url': "http://example.org/instagram"
    ...         },
    ...         {
    ...             'note': "homepage",
    ...             'url': "http://www.geocities.com"
    ...         },
    ...         {
    ...             'note': "homepage",
    ...             'url': "http://oops.duplicate.example.org"
    ...         }
    ...     ],
    ... }
    >>> update_values_in_sub_array(
    ...     person_data,
    ...     {'sub_array': 'links',
    ...      'info_type_key': 'note',
    ...      'info_value_key': 'url',
    ...      'info_type': 'homepage'},
    ...     "http://john.doe.example.org"
    ... )
    >>> update_values_in_sub_array(
    ...     person_data,
    ...     {'sub_array': 'links',
    ...      'info_type_key': 'note',
    ...      'info_value_key': 'url',
    ...      'info_type': 'myspace'},
    ...     ""
    ... )
    >>> update_values_in_sub_array(
    ...     person_data,
    ...     {'sub_array': 'links',
    ...      'info_type_key': 'note',
    ...      'info_value_key': 'url',
    ...      'info_type': 'instagram'},
    ...     ""
    ... )
   >>> print json.dumps(person_data, indent=4) # doctest: +NORMALIZE_WHITESPACE
    {
        "email": "john-doe@example.org",
        "id": "john-doe",
        "links": [
            {
                "note": "wikipedia",
                "url": "http://en.wikipedia.org/wiki/John_Doe"
            },
            {
                "note": "homepage",
                "url": "http://john.doe.example.org"
            }
        ],
        "name": "John Doe"
    }
    """
    new_info = [
        c for c in data.get(location['sub_array'], [])
        if c.get(location['info_type_key']) != location['info_type']
    ]
    if new_value:
        new_info.append({
            location['info_type_key']: location['info_type'],
            location['info_value_key']: new_value
        })
    data[location['sub_array']] = new_info
