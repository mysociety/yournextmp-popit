from copy import deepcopy
from datetime import date, timedelta
import json
import re
import sys
from collections import defaultdict

from slugify import slugify

from django.conf import settings
from django.core.urlresolvers import reverse
from django.utils.translation import ugettext as _
import django.dispatch
from django_date_extensions.fields import ApproximateDate
from slumber.exceptions import HttpServerError, HttpClientError

from .auth import (
    get_constituency_lock_from_person_data,
    check_creation_allowed,
    check_update_allowed,
)
from .db import MaxPopItIds

from ..cache import (
    get_person_cached, invalidate_person, get_post_cached, invalidate_posts
)
from ..diffs import get_version_diffs
from ..election_specific import (
    MAPIT_DATA, PARTY_DATA, AREA_POST_DATA,
    EXTRA_CSV_ROW_FIELDS, get_extra_csv_values
)

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
    'id',
    'name',
    'honorific_prefix',
    'honorific_suffix',
    'gender',
    'birth_date',
    'election',
    'party_id',
    'party_name',
    'post_id',
    'post_label',
    'mapit_url',
    'elected',
    'email',
    'twitter_username',
    'facebook_page_url',
    'party_ppc_page_url',
    'facebook_personal_url',
    'homepage_url',
    'wikipedia_url',
    'linkedin_url',
    'image_url',
    'proxy_image_url_template',
    'image_copyright',
    'image_uploading_user',
    'image_uploading_user_notes',
] + EXTRA_CSV_ROW_FIELDS


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
        'info_type': 'party candidate page',
        'old_info_type': 'party PPC page',
    }
}

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
    raise Exception, _("Couldn't parse '{0}' as an ApproximateDate").format(s)

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
        raise Exception, _("Unknown partial ISO 8601 data format: {0}").format(iso_8601_date_partial)

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
        # ID's format.  FIXME: don't do this; fetch the organization
        # to check the classification, so it's correct rather than
        # "probably right".
        party_id_match = re.search(
            r'^(party|ynmp-party|joint-party):',
            organization_id
        )
        special_party = (organization_id in ('unknown', 'not-listed'))
        return bool(party_id_match) or special_party

def is_candidacy_membership(membership):
    if not membership.get('election'):
        return False
    role = membership.get('role')
    election_data = settings.ELECTIONS[membership['election']]
    return role == election_data['candidate_membership_role']

def is_standing_in_membership(membership):
    return is_candidacy_membership(membership)

# FIXME: really this should be a method on a PopIt base class, so it's
# available for both people and organizations. (The same goes for
# set_identifier.)
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
        raise Exception(_("Failed to parse the MapIt URL: {0}").format(mapit_url))
    return m.group(1)

def create_or_update(api_collection, data):
    try:
        api_collection.post(data)
    except HttpServerError as hse:
        # If that already exists, use PUT to update the post instead:
        if 'E11000' in hse.content:
            api_collection(data['id']).put(data)
        else:
            raise

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

def election_to_party_dates(election):
    election_data = settings.ELECTIONS[election]
    return {
        'start_date': str(election_data['party_membership_start_date']),
        'end_date': str(election_data['party_membership_end_date']),
    }

def get_post_label_from_post_id(api, post_id):
    post_data = get_post_cached(api, post_id)
    return post_data['label']

def reduced_organization_data(organization):
    return {
        'id': organization['id'],
        'name': organization['name'],
    }

def get_value_from_location(location, person_data):
    for info in person_data.get(location['sub_array'], []):
        all_info_types = [location['info_type']]
        if 'old_info_type' in location:
            all_info_types.insert(0, location['old_info_type'])
        for info_type in all_info_types:
            if info[location['info_type_key']] == info_type:
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
                _("'PopItPerson' has no attribute '{0}'").format(name)
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
            raise Exception, _("There was no previous version of this person")
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

            for election, election_data in settings.ELECTIONS.items():
                if membership_covers_date(
                        membership,
                        election_data['election_date']
                ):
                    results[election] = organization
        return results

    @property
    def standing_in(self):
        return self.popit_data.get('standing_in', {}) or {}

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
        for election, constituency in v.items():
            if constituency:
                # i.e. we know that this isn't an indication that the
                # person isn't standing...
                # Create the candidate list membership:
                membership = election_to_party_dates(election)
                membership['election'] = election
                membership['person_id'] = self.id
                membership['post_id'] = constituency['post_id']
                candidate_role = settings.ELECTIONS[election]['candidate_membership_role']
                membership['role'] = candidate_role
                memberships.append(membership)
                if constituency.get('elected'):
                    day_after = settings.ELECTIONS[election]['election_date'] + \
                        timedelta(days=1)
                    memberships.append({
                        'start_date': str(day_after),
                        'end_date': '9999-12-31',
                        'person_id': self.id,
                        'post_id': constituency['post_id'],
                        # FIXME: https://github.com/mysociety/yournextrepresentative/issues/354
                        'organization_id': 'commons',
                    })

        self.popit_data['memberships'] = memberships
        self.popit_data['standing_in'] = v
        self.store_posts_for_invalidation()

    @property
    def party_memberships(self):
        return self.popit_data.get('party_memberships', {}) or {}

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
        for election, party in v.items():
            membership = election_to_party_dates(election)
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

    def known_status_in_election(self, election):
        standing_in = self.popit_data.get('standing_in', {}) or {}
        return election in standing_in

    def not_standing_in_election(self, election):
        # If there's a standing_in element present, and the value for
        # election is set to None, then someone has marked that person as
        # not standing...
        standing_in = self.popit_data.get('standing_in', {}) or {}
        return (election in standing_in) and standing_in[election] == None

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

    def as_dict(self, election):
        """
        Returns a dict with keys corresponding to the values in
        CSV_ROW_FIELDS, for ease of converting PopItPerson objects
        to CSV representations.
        """

        class EmptyForNoneAttributes(object):
            def __init__(self, person):
                self.person = person
            def __getattr__(self, name):
                value = getattr(self.person, name)
                if value is None:
                    return ''
                return value

        person_data = EmptyForNoneAttributes(self)
        post_id = self.standing_in[election]['post_id']

        # Get whether this candidate was a winner in this election:
        elected = self.get_elected(election)
        elected_for_csv = ''
        if elected is not None:
            elected_for_csv = str(elected)

        # Get all the image-related data:

        image = person_data.image
        proxy_image_url_template = ''
        image_copyright = ''
        image_uploading_user = ''
        image_uploading_user_notes = ''
        if image:
            proxy_image_url_template = \
                person_data.proxy_image + '/{width}/{height}.{extension}'
            image_data = self.popit_data['images'][0]
            image_copyright = image_data.get('moderator_why_allowed', '')
            image_uploading_user = image_data.get('uploaded_by_user', '')
            image_uploading_user_notes = \
                image_data.get('user_justification_for_use', '')

        row = {
            'id': self.id,
            'name': self.name,
            'honorific_prefix': person_data.honorific_prefix,
            'honorific_suffix': person_data.honorific_suffix,
            'gender': person_data.gender,
            'birth_date': person_data.birth_date,
            'election': election,
            'party_id': self.party_memberships[election]['id'],
            'party_name': self.party_memberships[election]['name'],
            'post_id': post_id,
            'post_label': self.standing_in[election]['name'],
            'mapit_url': self.standing_in[election]['mapit_url'],
            'elected': elected_for_csv,
            'email': person_data.email,
            'twitter_username': person_data.twitter_username,
            'facebook_page_url': person_data.facebook_page_url,
            'linkedin_url': person_data.linkedin_url,
            'party_ppc_page_url': person_data.party_ppc_page_url,
            'facebook_personal_url': person_data.facebook_personal_url,
            'homepage_url': person_data.homepage_url,
            'wikipedia_url': person_data.wikipedia_url,
            'image_url': image,
            'proxy_image_url_template': proxy_image_url_template,
            'image_copyright': image_copyright,
            'image_uploading_user': image_uploading_user,
            'image_uploading_user_notes': image_uploading_user_notes,
        }
        extra_csv_data = get_extra_csv_values(self, election, MAPIT_DATA)
        row.update(extra_csv_data)

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
        for election, election_data in settings.ELECTIONS_CURRENT:
            constituency_key = 'constituency_' + election
            standing_key = 'standing_' + election
            if election in self.standing_in:
                standing_in_election = self.standing_in[election]
                if standing_in_election:
                    initial_data[standing_key] = 'standing'
                    post_id = standing_in_election['post_id']
                    initial_data[constituency_key] = post_id
                    party_set = AREA_POST_DATA.post_id_to_party_set(post_id)
                    party_data = self.party_memberships.get(election, {})
                    party_id = party_data.get('id', '')
                    party_key = 'party_' + party_set + '_' + election
                    initial_data[party_key] = party_id
                else:
                    initial_data[standing_key] = 'not-standing'
                    initial_data[constituency_key] = ''
            else:
                initial_data[standing_key] = 'not-sure'
                initial_data[constituency_key] = ''

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
    def last_party_reduced(self):
        party = self.last_party
        if party:
            return reduced_organization_data(self.last_party)

    @property
    def last_cons(self):
        result = None
        for election, election_data in settings.ELECTIONS_BY_DATE:
            cons = self.popit_data['standing_in'].get(election)
            if cons:
                result = (election, cons, election_data['name'])
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

    def update_from_form(self, api, form):
        form_data = form.cleaned_data.copy()
        # The date is returned as a datetime.date, so if that's set, turn
        # it into a string:
        birth_date_date = form_data['birth_date']
        if birth_date_date:
            form_data['birth_date'] = repr(birth_date_date).replace("-00-00", "")
        else:
            form_data['birth_date'] = None

        new_standing_in = deepcopy(self.standing_in)
        new_party_memberships = deepcopy(self.party_memberships)

        for election, election_data in form.elections_with_fields:

            post_id = form_data.get('constituency_' + election)
            if post_id:
                party_set = AREA_POST_DATA.post_id_to_party_set(post_id)
                party_key = 'party_' + party_set + '_' + election
                form_data['party_' + election] = form_data[party_key]
            else:
                form_data['party_' + election] = None
            # Delete all the party set specific party information:
            for party_set in PARTY_DATA.ALL_PARTY_SETS:
                form_data.pop('party_' + party_set['slug']  + '_' + election)

            # Extract some fields that we will deal with separately:
            standing = form_data.pop('standing_' + election, 'standing')
            post_id = form_data.pop('constituency_' + election)
            party = form_data.pop('party_' + election)

            if standing == 'standing':
                post_data = get_post_cached(api, post_id)['result']
                post_label = post_data['label']
                new_standing_in[election] = {
                    'post_id': post_data['id'],
                    'name': AREA_POST_DATA.shorten_post_label(election, post_label),
                    'mapit_url': post_data['area']['identifier'],
                }
                # FIXME: stupid hack to preserve elected status after the election:
                old_standing_in = self.standing_in.get(election, {})
                if (old_standing_in is not None) and ('elected' in old_standing_in):
                    new_standing_in[election]['elected'] = old_standing_in['elected']
                new_party_memberships[election] = {
                    'name': PARTY_DATA.party_id_to_name[party],
                    'id': party,
                }
            elif standing == 'not-standing':
                # If the person is not standing in this election, record that
                # they're not and remove the party membership for the election:
                new_standing_in[election] = None
                if election in new_party_memberships:
                    del new_party_memberships[election]
            elif standing == 'not-sure':
                # If the update specifies that we're not sure if they're
                # standing in this election, then remove the standing_in and
                # party_memberships entries for that year:
                new_standing_in.pop(election, None)
                new_party_memberships.pop(election, None)

        self.standing_in = new_standing_in
        self.party_memberships = new_party_memberships

        # Now update the other fields:
        settable_fields = form_simple_fields.keys() + \
            form_complex_fields_locations.keys()
        for field in settable_fields:
            setattr(self, field, form_data[field])

    def set_elected(self, was_elected, election):
        standing_in = self.standing_in
        if not standing_in:
            message = _("Can't set_elected of a candidate with no standing_in")
            raise Exception, message
        if not standing_in.get(election):
            message = _("No standing_in information for {0}").format(election)
        if was_elected is None:
            del standing_in[election]['elected']
        else:
            standing_in[election]['elected'] = was_elected
        self.standing_in = standing_in

    def get_elected(self, election):
        standing_in = self.popit_data.get('standing_in') or {}
        if election not in standing_in:
            return None
        standing_in_election_data = standing_in.get(election, {})
        if not standing_in_election_data:
            return None
        return standing_in_election_data.get('elected')

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
    ...         },
    ...         {
    ...             'note': "party PPC page",
    ...             'url': "http://conservatives.example.org/foo"
    ...         },
    ...         {
    ...             'note': "party candidate page",
    ...             'url': "http://conservatives.example.org/bar"
    ...         },
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
    >>> update_values_in_sub_array(
    ...     person_data,
    ...     {'sub_array': 'links',
    ...      'info_type_key': 'note',
    ...      'info_value_key': 'url',
    ...      'info_type': 'party candidate page',
    ...      'old_info_type': 'party PPC page'},
    ...     "http://conservatives.example.org/newfoo"
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
            },
            {
                "note": "party candidate page",
                "url": "http://conservatives.example.org/newfoo"
            }
        ],
        "name": "John Doe"
    }
    """
    existing_info_types = [location['info_type']]
    if 'old_info_type' in location:
        existing_info_types.append(location['old_info_type'])
    new_info = [
        c for c in data.get(location['sub_array'], [])
        if c.get(location['info_type_key']) not in existing_info_types
    ]
    if new_value:
        new_info.append({
            location['info_type_key']: location['info_type'],
            location['info_value_key']: new_value
        })
    data[location['sub_array']] = new_info
