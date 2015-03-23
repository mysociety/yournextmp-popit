from datetime import date
import json
import jsonpatch
import jsonpointer
import re
import sys
from collections import defaultdict

from slugify import slugify

from django.contrib.auth.models import User
from django.db import models
from django.db.models.signals import post_save
from django.core.exceptions import ObjectDoesNotExist
from slumber.exceptions import HttpServerError

from .static_data import MapItData

form_simple_fields = (
    'honorific_prefix', 'name', 'honorific_suffix', 'email', 'birth_date',
    'gender'
)
preserve_fields = ('identifiers', 'other_names', 'phone')

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
    'linkedin_url',
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

election_date_2005 = date(2005, 5, 5)
election_date_2010 = date(2010, 5, 6)
election_date_2015 = date(2015, 5, 7)

all_form_fields = list(form_simple_fields) + form_complex_fields_locations.keys()

candidate_list_name_re = re.compile(r'^Candidates for (.*) in (\d+)$')

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

def create_person_with_id_retries(api, data, original_version):
    id_to_try = MaxPopItIds.get_max_persons_id() + 1
    while True:
        try:
            original_version['data']['id'] = data['id'] = str(id_to_try)
            data['versions'] = [original_version]
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


class StalePopItData(Exception):
    pass


class PopItPerson(object):

    def __init__(self, api=None, popit_data=None):
        self.popit_data = popit_data
        self.api = api

    def __eq__(self, other):
        return self.id == other.id

    def __hash__(self):
        return hash(self.id)

    @classmethod
    def create_from_popit(cls, api, popit_person_id):
        popit_data = api.persons(popit_person_id).get(
            embed='membership.organization')['result']
        new_person = cls(api=api, popit_data=popit_data)
        return new_person

    def update_from_popit(self, retry=None):
        kwargs = {
            'embed': 'membership.organization'
        }
        if retry is not None:
            kwargs['retry'] = str(retry)
        self.popit_data = self.api.persons(self.id).get(**kwargs)['result']

    @classmethod
    def create_from_dict(cls, person_dict):
        new_person = cls(popit_data=person_dict)
        return new_person

    @property
    def name(self):
        return self.popit_data['name']

    @property
    def id(self):
        return self.popit_data['id']

    @property
    def image(self):
        return self.popit_data.get('image')

    @property
    def parties(self):
        results = {}
        for membership in self.popit_data['memberships']:
            organization = membership.get('organization_id')
            if not organization:
                continue
            if organization['classification'] != "Party":
                continue
            if membership_covers_date(membership, election_date_2010):
                results['2010'] = organization
            if membership_covers_date(membership, election_date_2015):
                results['2015'] = organization
        return results

    @property
    def standing_in(self):
        """
        #   {
        #     '2010': {
        #       'name': 'South Cambridgeshire',
        #       'mapit_url': 'http://mapit.mysociety.org/area/65922',
        #       'post_id': 65922,
        #     }
        #   }
        """

        def post_id_to_cons_data(post_id):
            return {
                'name': get_constituency_name_from_mapit_id(post_id),
                'mapit_url': 'http://mapit.mysociety.org/area/{0}'.format(
                    post_id),
                'post_id': post_id,
            }

        # There's a tricky bug (in PopIt, I think) where we sometimes
        # get old data (that's missing memberships) back from PopIt,
        # but reloading again is fine. This is detectable because
        # standing_in has a non-None entry for 2015 that isn't
        # expressed by membership as well.  As a workaround, retry
        # getting the data from PopIt up to 5 times before giving up
        # and throwing an exception
        retry = 0
        while True:

            results = {}

            for membership in self.popit_data['memberships']:
                if membership.get('role') != "Candidate":
                    continue
                if 'post_id' not in membership:
                    continue
                if membership_covers_date(membership, election_date_2010):
                    results['2010'] = post_id_to_cons_data(membership['post_id'])
                if membership_covers_date(membership, election_date_2015):
                    results['2015'] = post_id_to_cons_data(membership['post_id'])

            # However, we can't infer from the candidate lists that
            # someone's a member of that we know that they're known not to
            # be standing in a particular election. So, if that
            # information is present in the PopIt data, set it in the
            # standing_in dictionary.
            standing_in = self.popit_data.get('standing_in') or {}
            for year, standing in standing_in.items():
                if standing:
                    # Then there must already be a corresponding candidate
                    # list membership, but check that:
                    if year not in results:
                        message = u"Missing post membership according to PopIt "
                        message += u"data for {0} in {1}. standing_in was {2}, "
                        message += u"memberships were {3}"
                        message = message.format(
                            self.id,
                            year,
                            self.popit_data.get('standing_in', 'MISSING'),
                            self.popit_data.get('memberships', 'MISSING'),
                        )
                        if retry <= 5:
                            print >> sys.stderr, message
                            retry += 1
                            self.update_from_popit(retry)
                            continue
                        else:
                            raise StalePopItData(message)
                else:
                    results[year] = None

            break

        return results

    @property
    def known_status_in_2015(self):
        standing_in = self.popit_data.get('standing_in', {})
        return '2015' in standing_in

    @property
    def not_standing_in_2015(self):
        # If there's a standing_in element present, its '2015' value
        # is set to None, then we someone has marked that person as
        # not standing...
        standing_in = self.popit_data.get('standing_in', {})
        return ('2015' in standing_in) and standing_in['2015'] == None

    def delete_memberships(self):
        for membership in self.popit_data.get('memberships', []):
            self.api.memberships(membership['id']).delete()

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
        }

        return row


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
    new_info.append({
        location['info_type_key']: location['info_type'],
        location['info_value_key']: new_value
    })
    data[location['sub_array']] = new_info

def get_person_data_from_dict(data):
    '''Convert our representation to person data can that be sent to PopIt

    Our representation is a flatter one, which corresponds in part to
    the fields in the "edit person" forms; in addition there are the
    'standing_in' and 'party_memberships' objects that are only used
    for creating memberships (i.e. not "person_data" in the sense of
    this method. There are also some fields that we should just
    preserve in this transformation, like 'identifiers'.'''
    result = {}
    # First deal with fields that simply map to top level fields in
    # Popolo.
    for field_name in form_simple_fields:
        if data.get(field_name):
            result[field_name] = unicode(data.get(field_name, ''))
        else:
            # Otherwise, set the field to null. (Empty string would
            # also do for any field except birth_date, which needs to
            # be null.) However, it's important that we *do* set all
            # fields to null or empty string, or they'll be left with
            # their old value.
            result[field_name] = None
    for field_name in preserve_fields:
        if field_name in data:
            result[field_name] = data[field_name]
    # These are fields which are represented by values in a sub-object
    # in Popolo's JSON serialization:
    for field_name, location in form_complex_fields_locations.items():
        new_value = data.get(field_name, '')
        if new_value:
            update_values_in_sub_array(result, location, new_value)
    return result


class MaxPopItIds(models.Model):
    popit_collection_name = models.CharField(max_length=255)
    max_id = models.IntegerField(default=0)

    @classmethod
    def get_max_persons_id(cls):
        try:
            return cls.objects.get(popit_collection_name="persons").max_id
        except ObjectDoesNotExist:
            persons_max = cls(popit_collection_name="persons")
            persons_max.save()
            return persons_max.max_id

    @classmethod
    def update_max_persons_id(cls, max_id):
        max_persons, created = cls.objects.get_or_create(
            popit_collection_name="persons")
        if max_id > max_persons.max_id:
            max_persons.max_id = max_id
            max_persons.save()
        else:
            raise ValueError('given max_id is lower than the previous one ({'
                             '0} vs {1})'.format(max_id, max_persons.max_id))


class LoggedAction(models.Model):
    '''A model for logging the actions of users on the site

    We record the changes that have been made to a person in PopIt in
    that person's 'versions' field, but is not much help for queries
    like "what has John Q User been doing on the site?". The
    LoggedAction model makes that kind of query easy, however, and
    should be helpful in tracking down both bugs and the actions of
    malicious users.'''

    user = models.ForeignKey(User, blank=True, null=True)
    action_type = models.CharField(max_length=64)
    popit_person_new_version = models.CharField(max_length=32)
    popit_person_id = models.CharField(max_length=256)
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)
    ip_address = models.CharField(max_length=50, blank=True, null=True)
    source = models.TextField()


class PersonRedirect(models.Model):
    '''This represents a redirection from one person ID to another

    This is typically used to redirect from the person that is deleted
    after two people are merged'''
    old_person_id = models.IntegerField()
    new_person_id = models.IntegerField()


class UserTermsAgreement(models.Model):
    user = models.OneToOneField(User, related_name='terms_agreement')
    assigned_to_dc = models.BooleanField(default=False)


def create_user_terms_agreement(sender, instance, created, **kwargs):
    if created:
        UserTermsAgreement.objects.create(user=instance)

post_save.connect(create_user_terms_agreement, sender=User)
