from __future__ import unicode_literals

from datetime import date
import json
from os.path import join
import re

from django.conf import settings
from django.contrib.auth.models import User
from django.contrib.contenttypes.fields import GenericRelation
from django.core.exceptions import ObjectDoesNotExist
from django.core.files.storage import FileSystemStorage
from django.core.urlresolvers import reverse
from django.db import models
from django.template import loader, Context
from django.utils.functional import cached_property
from django.utils.translation import ugettext as _
from django.utils.translation import ugettext_lazy as _l
from django.utils.six.moves.urllib_parse import urljoin, quote_plus

from usersettings.shortcuts import get_current_usersettings

from dateutil import parser
from slugify import slugify
from django_date_extensions.fields import ApproximateDate

from elections.models import Election, AreaType
from popolo.models import (
    ContactDetail, Person, Organization, Post, Membership, Area, Identifier
)
from images.models import Image, HasImageMixin

from compat import python_2_unicode_compatible
from .fields import (
    ExtraField, PersonExtraFieldValue, SimplePopoloField, ComplexPopoloField,
    get_complex_popolo_fields,
)
from ..diffs import get_version_diffs
from ..twitter_api import update_twitter_user_id, TwitterAPITokenMissing
from .sitesettings import get_site_setting
from .versions import get_person_as_version_data

"""Extensions to the base django-popolo classes for YourNextRepresentative

These are done via explicit one-to-one fields to avoid the performance
problems with multi-table inheritance; it's preferable to state when you
want a join or not.

  http://stackoverflow.com/q/23466577/223092

"""

def update_person_from_form(person, person_extra, form):
    form_data = form.cleaned_data.copy()
    # The date is returned as a datetime.date, so if that's set, turn
    # it into a string:
    birth_date_date = form_data['birth_date']
    if birth_date_date:
        form_data['birth_date'] = repr(birth_date_date).replace("-00-00", "")
    else:
        form_data['birth_date'] = ''
    for field in SimplePopoloField.objects.all():
        setattr(person, field.name, form_data[field.name])
    for field in ComplexPopoloField.objects.all():
        person_extra.update_complex_field(field, form_data[field.name])
    for extra_field in ExtraField.objects.all():
        if extra_field.key in form_data:
            PersonExtraFieldValue.objects.update_or_create(
                person=person, field=extra_field,
                defaults={'value': form_data[extra_field.key]}
            )
    if 'marked_for_review' in form_data:
        person_extra.marked_for_review = form_data['marked_for_review']
    person.save()
    person_extra.save()
    try:
        update_twitter_user_id(person)
    except TwitterAPITokenMissing:
        pass
    for election_data in form.elections_with_fields:
        post_id = form_data.get('constituency_' + election_data.slug)
        standing = form_data.pop('standing_' + election_data.slug, 'standing')
        if post_id:
            party_set = PartySet.objects.get(postextra__slug=post_id)
            party_key = 'party_' + party_set.slug + '_' + election_data.slug
            position_key = \
                'party_list_position_' + party_set.slug + '_' + election_data.slug
            party = Organization.objects.get(pk=form_data[party_key])
            party_list_position = form_data.get(position_key) or None
            post = Post.objects.get(extra__slug=post_id)
        else:
            party = None
            party_list_position = None
        # Get a queryset of the existing candidacies:
        candidacy_qs = Membership.objects.filter(
            extra__election=election_data,
            role=election_data.candidate_membership_role,
            person__extra=person_extra
        )
        # Preserve the 'elected' property of MembershipExtra, which
        # isn't in the form:
        elected_saved = dict(
            candidacy_qs.values_list('extra__election__slug', 'extra__elected')
        )
        # Remove any existing memberships; we'll recreate them if the
        # person's actually standing. (Since MembershipExtra depends
        # on Membership, this will delete any corresponding Membership.)
        candidacy_qs.delete()
        # Remove any indication that they're not standing in that
        # election. Similarly we'll recreate it if necessary:
        person_extra.not_standing.remove(election_data)
        if standing == 'standing':
            # Create the new membership:
            membership = Membership.objects.create(
                post=post,
                on_behalf_of=party,
                person=person,
                role=election_data.candidate_membership_role,
            )
            MembershipExtra.objects.create(
                base=membership,
                party_list_position=party_list_position,
                election=election_data,
                elected=elected_saved.get(election_data.slug)
            )
        elif standing == 'not-standing':
            person_extra.not_standing.add(election_data)


def squash_whitespace(s):
    # Take any run of more than one whitespace character, and replace
    # it either with a newline (if that replaced text contained a
    # newline) or a space (otherwise).
    return re.sub(
        r'(?ims)\s+',
        lambda m: '\n' if '\n' in m.group(0) else ' ',
        s)


class localparserinfo(parser.parserinfo):
    MONTHS = [
        ('Jan', _l('Jan'), 'January', _l('January')),
        ('Feb', _l('Feb'), 'February', _l('February')),
        ('Mar', _l('Mar'), 'March', _l('March')),
        ('Apr', _l('Apr'), 'April', _l('April')),
        ('May', _l('May'), 'May', _l('May')),
        ('Jun', _l('Jun'), 'June', _l('June')),
        ('Jul', _l('Jul'), 'July', _l('July')),
        ('Aug', _l('Aug'), 'August', _l('August')),
        ('Sep', _l('Sep'), 'Sept', 'September', _l('September')),
        ('Oct', _l('Oct'), 'October', _l('October')),
        ('Nov', _l('Nov'), 'November', _l('November')),
        ('Dec', _l('Dec'), 'December', _l('December'))
    ]

    PERTAIN = ['of', _l('of')]


def parse_approximate_date(s):
    """Take any reasonable date string, and return an ApproximateDate for it

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

    user_settings = get_current_usersettings()

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
    if s:
        dt = parser.parse(
            s,
            parserinfo=localparserinfo(),
            dayfirst=user_settings.DD_MM_DATE_FORMAT_PREFERRED
        )
        return ApproximateDate(dt.year, dt.month, dt.day)
    raise ValueError("Couldn't parse '{0}' as an ApproximateDate".format(s))


class PersonExtraQuerySet(models.QuerySet):

    def missing(self, field):
        people_in_current_elections = self.filter(
            base__memberships__extra__election__current=True
        )
        # The field can be one of several types:
        simple_field = SimplePopoloField.objects.filter(name=field).first()
        if simple_field:
            return people_in_current_elections.filter(**{'base__' + field: ''})
        complex_field = ComplexPopoloField.objects.filter(name=field).first()
        if complex_field:
            kwargs = {
                'base__{relation}__{key}'.format(
                    relation=complex_field.popolo_array,
                    key=complex_field.info_type_key
                ):
                complex_field.info_type
            }
            return people_in_current_elections.exclude(**kwargs)
        extra_field = ExtraField.objects.filter(key=field).first()
        if extra_field:
            # This case is a bit more complicated because the
            # PersonExtraFieldValue class allows a blank value.
            pefv_completed = PersonExtraFieldValue.objects.filter(
                field=extra_field
            ).exclude(value='')
            return people_in_current_elections.exclude(
                base__id__in=[pefv.person_id for pefv in pefv_completed]
            )
        # If we get to this point, it's a non-existent field on the person:
        raise ValueError("Unknown field '{0}'".format(field))

    def joins_for_csv_output(self):
        return self.select_related('base') \
            .prefetch_related(
                models.Prefetch(
                    'base__memberships',
                    Membership.objects.select_related(
                        'extra',
                        'extra__election',
                        'on_behalf_of__extra',
                        'post__area',
                        'post__extra',
                    ).prefetch_related(
                        'on_behalf_of__identifiers',
                        'post__area__other_identifiers',
                    )
                ),
                'base__contact_details',
                'base__identifiers',
                'base__links',
                'images__extra__uploading_user',
            )


class MultipleTwitterIdentifiers(Exception):
    pass


class VersionNotFound(Exception):
    pass


@python_2_unicode_compatible
class PersonExtra(HasImageMixin, models.Model):
    base = models.OneToOneField(Person, related_name='extra')

    # This field stores JSON data with previous version information
    # (as it did in PopIt).
    versions = models.TextField(blank=True)

    marked_for_review = models.BooleanField(default=False)

    images = GenericRelation(Image)

    objects = PersonExtraQuerySet.as_manager()

    @cached_property
    def complex_popolo_fields(self):
        return get_complex_popolo_fields()

    def __getattr__(self, name):
        # We don't want to trigger the population of the
        # complex_popolo_fields property just because Django is
        # checking whether the prefetch objects cache is there:
        if name == '_prefetched_objects_cache':
            return super(PersonExtra, self).__getattr__(self, name)
        field = self.complex_popolo_fields.get(name)
        if field:
            # Iterate rather than using filter because that would
            # cause an extra query when the relation has already been
            # populated via select_related:
            for e in getattr(self.base, field.popolo_array).all():
                info_type_key = getattr(e, field.info_type_key)
                if (info_type_key == field.info_type) or \
                   (info_type_key == field.old_info_type):
                    return getattr(e, field.info_value_key)
            return ''
        else:
            message = _("'PersonExtra' object has no attribute '{name}'")
            raise AttributeError(message.format(name=name))

    def get_slug(self):
        return slugify(self.base.name)

    def get_absolute_url(self, request=None):
        path = reverse(
            'person-view',
            kwargs={
                'person_id': self.base.id,
                'ignored_slug': self.get_slug(),
            }
        )
        if request is None:
            return path
        return request.build_absolute_uri(path)

    @property
    def current_candidacies(self):
        result = self.base.memberships.filter(
            extra__election__current=True,
            role=models.F('extra__election__candidate_membership_role')
        ).select_related('person', 'on_behalf_of', 'post') \
            .prefetch_related('post__extra')
        return list(result)

    @property
    def last_candidacy(self):
        ordered_candidacies = Membership.objects. \
            filter(person=self.base, extra__election__isnull=False). \
            order_by('extra__election__current', 'extra__election__election_date')
        return ordered_candidacies.last()

    def last_party(self):
        last_candidacy = self.last_candidacy
        if last_candidacy is None:
            return None
        return last_candidacy.on_behalf_of

    def name_with_honorifics(self):
        name_parts = []
        pre = self.base.honorific_prefix
        post = self.base.honorific_suffix
        if pre:
            name_parts.append(pre)
        name_parts.append(self.base.name)
        if post:
            name_parts.append(post)
        return ' '.join(name_parts)

    @property
    def dob_as_approximate_date(self):
        return parse_approximate_date(self.base.birth_date)

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
        return _("{min_age} or {max_age}").format(min_age=min_age,
                                                  max_age=max_age)

    """
    Return the elected state for a person in an election.
    Takes the election object as an arg.
    Returns True if they were elected, False if not and None if
    the results have not been set.
    This assumes that someone can only be elected in a single
    post in any election.
    """
    def get_elected(self, election):
        role = election.candidate_membership_role
        if role is None:
            role = ''
        membership = self.base.memberships \
            .select_related('extra') \
            .filter(
                role=role,
                extra__election=election,
            )

        result = membership.first()
        if result:
            return result.extra.elected

        return None

    @property
    def twitter_identifiers(self):
        screen_name = None
        user_id = None
        # Get the Twitter screen name and user ID if they exist:
        try:
            screen_name = self.base.contact_details \
                .get(contact_type='twitter').value
        except ContactDetail.DoesNotExist:
            screen_name = None
        except ContactDetail.MultipleObjectsReturned:
            msg = "Multiple Twitter screen names found for {name} ({id})"
            raise MultipleTwitterIdentifiers(
                _(msg).format(name=self.base.name, id=self.base.id))
        try:
            user_id = self.base.identifiers \
                .get(scheme='twitter').identifier
        except Identifier.DoesNotExist:
            user_id = None
        except Identifier.MultipleObjectsReturned:
            msg = "Multiple Twitter user IDs found for {name} ({id})"
            raise MultipleTwitterIdentifiers(
                _(msg).format(name=self.base.name, id=self.base.id))
        return user_id, screen_name

    @property
    def version_diffs(self):
        versions = self.versions
        if not versions:
            versions = []
        return get_version_diffs(json.loads(versions))

    def diff_for_version(self, version_id, inline_style=False):
        versions = self.versions or []
        all_version_diffs = get_version_diffs(json.loads(versions))
        right_version_diff = None
        for version_diff in all_version_diffs:
            if version_diff['version_id'] == version_id:
                right_version_diff = version_diff
                break
        if not right_version_diff:
            msg = "Couldn't find version {0} for person with ID {1}"
            raise VersionNotFound(msg.format(version_id, self.base.id))
        template = loader.get_template('candidates/_diffs_against_parents.html')
        context = Context({
            'diffs_against_all_parents': right_version_diff['diffs'],
            'inline_style': inline_style,
        })
        rendered = template.render(context)
        return squash_whitespace('<dl>{0}</dl>'.format(rendered))

    def record_version(self, change_metadata):
        versions = []
        if self.versions:
            versions = json.loads(self.versions)
        new_version = change_metadata.copy()
        new_version['data'] = get_person_as_version_data(self.base)
        versions.insert(0, new_version)
        self.versions = json.dumps(versions)

    def update_complex_field(self, location, new_value):
        existing_info_types = [location.info_type]
        if location.old_info_type:
            existing_info_types.append(location.old_info_type)
        related_manager = getattr(self.base, location.popolo_array)
        # Remove the old entries of that type:
        kwargs = {
            (location.info_type_key + '__in'): existing_info_types
        }
        related_manager.filter(**kwargs).delete()
        if new_value:
            kwargs = {
                location.info_type_key: location.info_type,
                location.info_value_key: new_value,
            }
            related_manager.create(**kwargs)

    def get_initial_form_data(self):
        initial_data = {}
        for field in SimplePopoloField.objects.all():
            initial_data[field.name] = getattr(self.base, field.name)
        for field in ComplexPopoloField.objects.all():
            initial_data[field.name] = getattr(self, field.name)
        for extra_field_value in PersonExtraFieldValue.objects.filter(
                person=self.base
        ).select_related('field'):
            initial_data[extra_field_value.field.key] = extra_field_value.value
        initial_data['marked_for_review'] = self.marked_for_review
        not_standing_elections = set(self.not_standing.all())
        election_to_membershipextra = {
            me.election: me for me in
            MembershipExtra.objects.filter(
                base__person__extra=self,
                election__current=True,
            ).select_related(
                'election',
                'base__post__extra',
                'base__on_behalf_of',
            )
        }
        for election_data in Election.objects.current().by_date():
            constituency_key = 'constituency_' + election_data.slug
            standing_key = 'standing_' + election_data.slug
            candidacy = election_to_membershipextra.get(election_data)
            if election_data in not_standing_elections:
                initial_data[standing_key] = 'not-standing'
            elif candidacy:
                initial_data[standing_key] = 'standing'
                post_id = candidacy.base.post.extra.slug
                initial_data[constituency_key] = post_id
                party_set = PartySet.objects.get(postextra__slug=post_id)
                party = candidacy.base.on_behalf_of
                party_key = 'party_' + party_set.slug + '_' + election_data.slug
                initial_data[party_key] = party.id
                position = candidacy.party_list_position
                position_key = 'party_list_position_' + party_set.slug + '_' + election_data.slug
                if position:
                    initial_data[position_key] = position
            else:
                initial_data[standing_key] = 'not-sure'
                initial_data[constituency_key] = ''
        return initial_data

    def update_from_form(self, form):
        update_person_from_form(self.base, self, form)

    @classmethod
    def create_from_form(cls, form):
        person = Person.objects.create(
            name=form.cleaned_data['name'],
        )
        person_extra = PersonExtra.objects.create(
            base=person,
        )
        update_person_from_form(person, person_extra, form)
        return person_extra

    def as_list_of_dicts(self, election, base_url=None):
        result = []
        user_settings = get_current_usersettings()
        if not base_url:
            base_url = ''
        # Find the list of relevant candidacies. So as not to cause
        # extra queries, we don't use filter but instead iterate over
        # all objects:
        candidacies = []
        for m in self.base.memberships.all():
            try:
                m_extra = m.extra
            except ObjectDoesNotExist:
                continue
            if not m_extra.election:
                continue
            expected_role = m.extra.election.candidate_membership_role
            if election is None:
                if expected_role == m.role:
                    candidacies.append(m)
            else:
                if m_extra.election == election and expected_role == m.role:
                    candidacies.append(m)
        for candidacy in candidacies:
            candidacy_extra = candidacy.extra
            party = candidacy.on_behalf_of
            post = candidacy.post
            elected = candidacy_extra.elected
            elected_for_csv = ''
            image_copyright = ''
            image_uploading_user = ''
            image_uploading_user_notes = ''
            proxy_image_url_template = ''
            if elected is not None:
                elected_for_csv = str(elected)
            mapit_identifier = None
            for identifier in post.area.other_identifiers.all():
                if identifier.scheme == 'mapit-area-url':
                    mapit_identifier = identifier
            if mapit_identifier:
                mapit_url = mapit_identifier.identifier
            else:
                mapit_url = ''
            primary_image = None
            for image in self.images.all():
                if image.is_primary:
                    primary_image = image
            primary_image_url = None
            if primary_image:
                primary_image_url = urljoin(base_url, primary_image.image.url)
                if user_settings.IMAGE_PROXY_URL and base_url:
                    encoded_url = quote_plus(primary_image_url)
                    proxy_image_url_template = user_settings.IMAGE_PROXY_URL + \
                        encoded_url + '/{height}/{width}.{extension}'

                try:
                    image_copyright = primary_image.extra.copyright
                    user = primary_image.extra.uploading_user
                    if user is not None:
                        image_uploading_user = primary_image.extra.uploading_user.username
                    image_uploading_user_notes = primary_image.extra.user_notes
                except ObjectDoesNotExist:
                    pass
            twitter_user_id = ''
            for identifier in self.base.identifiers.all():
                if identifier.scheme == 'twitter':
                    twitter_user_id = identifier.identifier

            row = {
                'id': self.base.id,
                'name': self.base.name,
                'honorific_prefix': self.base.honorific_prefix,
                'honorific_suffix': self.base.honorific_suffix,
                'gender': self.base.gender,
                'birth_date': self.base.birth_date,
                'election': candidacy_extra.election.slug,
                'election_date': candidacy_extra.election.election_date,
                'election_current': candidacy_extra.election.current,
                'party_id': party.extra.slug,
                'party_lists_in_use': candidacy_extra.election.party_lists_in_use,
                'party_list_position': candidacy_extra.party_list_position,
                'party_name': party.name,
                'post_id': post.extra.slug,
                'post_label': post.extra.short_label,
                'mapit_url': mapit_url,
                'elected': elected_for_csv,
                'email': self.base.email,
                'twitter_username': self.twitter_username,
                'twitter_user_id': twitter_user_id,
                'facebook_page_url': self.facebook_page_url,
                'linkedin_url': self.linkedin_url,
                'party_ppc_page_url': self.party_ppc_page_url,
                'facebook_personal_url': self.facebook_personal_url,
                'homepage_url': self.homepage_url,
                'wikipedia_url': self.wikipedia_url,
                'image_url': primary_image_url,
                'proxy_image_url_template': proxy_image_url_template,
                'image_copyright': image_copyright,
                'image_uploading_user': image_uploading_user,
                'image_uploading_user_notes': image_uploading_user_notes,
            }
            from ..election_specific import get_extra_csv_values
            extra_csv_data = get_extra_csv_values(self.base, election, post)
            row.update(extra_csv_data)
            result.append(row)

        return result

    not_standing = models.ManyToManyField(
        Election, related_name='persons_not_standing'
    )

    def __str__(self):
        # WARNING: This will cause an extra query when getting the
        # repr() or unicode() of this object unless the base object
        # has been select_related.
        return self.base.name


@python_2_unicode_compatible
class OrganizationExtra(HasImageMixin, models.Model):
    base = models.OneToOneField(Organization, related_name='extra')
    slug = models.CharField(max_length=256, blank=True, unique=True)

    # For parties, which party register is it on:
    register = models.CharField(blank=True, max_length=512)

    images = GenericRelation(Image)

    def __str__(self):
        # WARNING: This will cause an extra query when getting the
        # repr() or unicode() of this object unless the base object
        # has been select_related.
        return self.base.name


@python_2_unicode_compatible
class PostExtra(HasImageMixin, models.Model):
    base = models.OneToOneField(Post, related_name='extra')
    slug = models.CharField(max_length=256, blank=True, unique=True)

    candidates_locked = models.BooleanField(default=False)
    elections = models.ManyToManyField(
        Election,
        related_name='posts',
        through='PostExtraElection'
    )
    group = models.CharField(max_length=1024, blank=True)
    party_set = models.ForeignKey('PartySet', blank=True, null=True)

    def __str__(self):
        # WARNING: This will cause an extra query when getting the
        # repr() or unicode() of this object unless the base object
        # has been select_related.
        return self.base.label

    @property
    def short_label(self):
        from candidates.election_specific import shorten_post_label
        return shorten_post_label(self.base.label)


class PostExtraElection(models.Model):
    postextra = models.ForeignKey(PostExtra)
    election = models.ForeignKey(Election)

    winner_count = models.IntegerField(blank=True, null=True)


class MembershipExtra(models.Model):
    base = models.OneToOneField(Membership, related_name='extra')

    elected = models.NullBooleanField()
    party_list_position = models.IntegerField(null=True)
    election = models.ForeignKey(
        Election, blank=True, null=True, related_name='candidacies'
    )


@python_2_unicode_compatible
class AreaExtra(models.Model):
    base = models.OneToOneField(Area, related_name='extra')

    type = models.ForeignKey(AreaType, blank=True, null=True, related_name='areas')

    def __str__(self):
        # WARNING: This will cause an extra query when getting the
        # repr() or unicode() of this object unless the base object
        # has been select_related.
        return self.base.name


@python_2_unicode_compatible
class PartySet(models.Model):
    slug = models.CharField(max_length=256, unique=True)
    name = models.CharField(max_length=1024)
    parties = models.ManyToManyField(Organization, related_name='party_sets')

    def __str__(self):
        return self.name

    def party_choices_basic(self):
        result = list(self.parties.order_by('name').values_list('id', 'name'))
        result.insert(0, ('party:none', ''))
        return result

    def party_choices(self):
        # For various reasons, we've found it's best to order the
        # parties by those that have the most candidates - this means
        # that the commonest parties to select are at the top of the
        # drop down.  The logic here tries to build such an ordered
        # list of candidates if there are enough that such an ordering
        # makes sense.  Otherwise the fallback is to rank
        # alphabetically.
        candidacies_current_qs = Membership.objects.filter(
            extra__election__current=True,
            role=models.F('extra__election__candidate_membership_role'),
            on_behalf_of__party_sets=self,
        )
        candidacies_ever_qs =  Membership.objects.filter(
            role=models.F('extra__election__candidate_membership_role'),
            on_behalf_of__party_sets=self,
        )
        minimum_count = get_site_setting(
            'CANDIDATES_REQUIRED_FOR_WEIGHTED_PARTY_LIST')
        qs = None
        if candidacies_current_qs.count() > minimum_count:
            qs = candidacies_current_qs
        elif candidacies_ever_qs.count() > minimum_count:
            qs = candidacies_ever_qs
        else:
            return self.party_choices_basic()
        result = [('party:none', '')]
        parties_with_candidates = []
        for party_tuple in qs \
                .values('on_behalf_of', 'on_behalf_of__name') \
                .order_by() \
                .annotate(party_count=models.Count('pk')) \
                .order_by('-party_count', 'on_behalf_of__name'):
            parties_with_candidates.append(party_tuple['on_behalf_of'])
            name_with_count = \
                _('{party_name} ({number_of_candidates} candidates)').format(
                    party_name=party_tuple['on_behalf_of__name'],
                    number_of_candidates=party_tuple['party_count']
                )
            result.append(
                (party_tuple['on_behalf_of'], name_with_count)
            )
        result += self.parties.exclude(id__in=parties_with_candidates) \
            .order_by('name').values_list('id', 'name')
        return result


class ImageExtraManager(models.Manager):

    def create_from_file(
            self, image_filename, ideal_relative_name, base_kwargs, extra_kwargs
    ):
        # Import the file to media root and create the ORM
        # objects.
        storage = FileSystemStorage()
        desired_storage_path = join('images', ideal_relative_name)
        with open(image_filename, 'rb') as f:
            storage_filename = storage.save(desired_storage_path, f)
        image = Image.objects.create(image=storage_filename, **base_kwargs)
        return ImageExtra.objects.create(base=image, **extra_kwargs)

    def update_or_create_from_file(
            self, image_filename, ideal_relative_name, defaults, **kwargs
    ):
        try:
            image_extra = ImageExtra.objects \
                .select_related('base').get(**kwargs)
            for k, v in defaults.items():
                if k.startswith('base__'):
                    base_k = re.sub(r'^base__', '', k)
                    setattr(image_extra.base, base_k, v)
                else:
                    setattr(image_extra, k, v)
            image_extra.save()
            image_extra.base.save()
            return image_extra, False
        except ImageExtra.DoesNotExist:
            # Prepare args for the base object first:
            base_kwargs = {
                re.sub(r'base__', '', k): v for k, v in defaults.items()
                if k.startswith('base__')
            }
            base_kwargs.update({
                re.sub(r'base__', '', k): v for k, v in kwargs.items()
                if k.startswith('base__')
            })
            # And now the extra object:
            extra_kwargs = {
                k: v for k, v in defaults.items() if not k.startswith('base__')
            }
            extra_kwargs.update({
                k: v for k, v in kwargs.items() if not k.startswith('base__')
            })
            image_extra = self.create_from_file(
                image_filename, ideal_relative_name, base_kwargs, extra_kwargs
            )
        return image_extra


class ImageExtra(models.Model):
    base = models.OneToOneField(Image, related_name='extra')

    copyright = models.CharField(max_length=64, default='other', blank=True)
    uploading_user = models.ForeignKey(User, blank=True, null=True)
    user_notes = models.TextField(blank=True)
    md5sum = models.CharField(max_length=32, blank=True)
    user_copyright = models.CharField(max_length=128, blank=True)
    notes = models.TextField(blank=True)

    objects = ImageExtraManager()
