# -*- coding: utf-8 -*-

import re

from .cache import get_post_cached, get_all_posts_cached, UnknownPostException
from .popit import create_popit_api_object, PopItApiMixin
from .election_specific import PARTY_DATA, AREA_POST_DATA
from .models.address import check_address

from django import forms
from django.conf import settings
from django.contrib.sites.models import Site
from django.core.exceptions import ValidationError
from django.utils.translation import ugettext_lazy as _

from django_date_extensions.fields import ApproximateDateFormField

class AddressForm(forms.Form):
    address = forms.CharField(
        label=_('Enter your address or town'),
        max_length=2048,
    )

    def __init__(self, country, *args, **kwargs):
        super(AddressForm, self).__init__(*args, **kwargs)
        self.country = country

    def clean_address(self):
        address = self.cleaned_data['address']
        check_address(address, self.country)
        return address


class BaseCandidacyForm(forms.Form):
    person_id = forms.CharField(
        label=_('Person ID'),
        max_length=256,
    )
    post_id = forms.CharField(
        label=_('Post ID'),
        max_length=256,
    )

class CandidacyCreateForm(BaseCandidacyForm):
    source = forms.CharField(
        label=_(u"Source of information that they're standing ({0})").format(
            settings.SOURCE_HINTS
        ),
        max_length=512,
    )

class CandidacyDeleteForm(BaseCandidacyForm):
    source = forms.CharField(
        label=_(u"Information source for this change ({0})").format(
            settings.SOURCE_HINTS
        ),
        max_length=512,
    )

class BasePersonForm(PopItApiMixin, forms.Form):

    STANDING_CHOICES = (
        ('not-sure', _(u"Don’t Know")),
        ('standing', _(u"Yes")),
        ('not-standing', _(u"No")),
    )

    honorific_prefix = forms.CharField(
        label=_("Title / pre-nominal honorific (e.g. Dr, Sir, etc.)"),
        max_length=256,
        required=False,
    )
    name = forms.CharField(
        label=_("Full name"),
        max_length=1024,
    )
    honorific_suffix = forms.CharField(
        label=_("Post-nominal letters (e.g. CBE, DSO, etc.)"),
        max_length=256,
        required=False,
    )
    email = forms.EmailField(
        label=_("Email"),
        max_length=256,
        required=False,
    )
    gender = forms.CharField(
        label=_(u"Gender (e.g. “male”, “female”)"),
        max_length=256,
        required=False,
    )
    birth_date = ApproximateDateFormField(
        label=_("Date of birth (as YYYY-MM-DD or YYYY)"),
        required=False,
    )
    wikipedia_url = forms.URLField(
        label=_("Wikipedia URL"),
        max_length=256,
        required=False,
    )
    homepage_url = forms.URLField(
        label=_("Homepage URL"),
        max_length=256,
        required=False,
    )
    twitter_username = forms.CharField(
        label=_(u"Twitter username (e.g. “democlub”)"),
        max_length=256,
        required=False,
    )
    facebook_personal_url = forms.URLField(
        label=_("Facebook profile URL"),
        max_length=256,
        required=False,
    )
    facebook_page_url = forms.URLField(
        label=_("Facebook page (e.g. for their campaign)"),
        max_length=256,
        required=False,
    )
    linkedin_url = forms.URLField(
        label=_("LinkedIn URL"),
        max_length=256,
        required=False,
    )
    party_ppc_page_url = forms.URLField(
        label=_(u"The party’s candidate page for this person"),
        max_length=256,
        required=False,
    )

    def clean_twitter_username(self):
        # Remove any URL bits around it:
        username = self.cleaned_data['twitter_username'].strip()
        m = re.search('^.*twitter.com/(\w+)', username)
        if m:
            username = m.group(1)
        # If there's a leading '@', strip that off:
        username = re.sub(r'^@', '', username)
        if not re.search(r'^\w*$', username):
            message = _("The Twitter username must only consist of alphanumeric characters or underscore")
            raise ValidationError(message)
        return username

    def check_party_and_constituency_are_selected(self, cleaned_data):
        '''This is called by the clean method of subclasses'''

        for election, election_data in self.elections_with_fields:
            election_name = election_data['name']

            standing_status = cleaned_data.get(
                'standing_' + election, 'standing'
            )
            if standing_status != 'standing':
               continue

            # Make sure that there is a party selected; we need to do this
            # from the clean method rather than single field validation
            # since the party field that should be checked depends on the
            # selected constituency.
            post_id = cleaned_data['constituency_' + election]
            if not post_id:
                message = _("If you mark the candidate as standing in the "
                            "{election}, you must select a post")
                raise forms.ValidationError(message.format(
                    election=election_name
                ))
            # Check that that post actually exists:
            try:
                get_post_cached(self.api, post_id)
            except UnknownPostException:
                message = _("An unknown post ID '{post_id}' was specified")
                raise forms.ValidationError(
                    message.format(post_id=post_id)
                )
            party_set = AREA_POST_DATA.post_id_to_party_set(post_id)
            if not party_set:
                message = _("Could not find parties for the post with ID "
                            "'{post_id}' in the {election}")
                raise forms.ValidationError(
                    message.format(post_id=post_id, election=election_name)
                )
            party_field = 'party_' + party_set + '_' + election
            party_id = cleaned_data[party_field]
            if party_id not in PARTY_DATA.party_id_to_name:
                message = _("You must specify a party for the {election}")
                raise forms.ValidationError(message.format(election=election_name))
        return cleaned_data


class NewPersonForm(BasePersonForm):

    def __init__(self, *args, **kwargs):
        election = kwargs.pop('election', None)
        hidden_post_widget = kwargs.pop('hidden_post_widget', None)
        super(NewPersonForm, self).__init__(*args, **kwargs)

        if election not in settings.ELECTIONS:
            raise Exception, _("Unknown election: '{election}'").format(election=election)

        election_data = settings.ELECTIONS[election]
        role = election_data['for_post_role']

        standing_field_kwargs = {
            'label': _('Standing in %s') % election_data['name'],
            'choices': self.STANDING_CHOICES,
        }
        if hidden_post_widget:
            standing_field_kwargs['widget'] = forms.HiddenInput()
        else:
            standing_field_kwargs['widget'] = forms.Select(attrs={'class': 'standing-select'})
        self.fields['standing_' + election] = \
            forms.ChoiceField(**standing_field_kwargs)

        self.elections_with_fields = [
            (election, election_data)
        ]

        post_field_kwargs = {
            'label': _("Post in the {election}").format(
                election=election_data['name']
            ),
            'max_length': 256,
        }
        if hidden_post_widget:
            post_field_kwargs['widget'] = forms.HiddenInput()
            post_field = forms.CharField(**post_field_kwargs)
        else:
            post_field = \
                forms.ChoiceField(
                    label=_('Post in the {election}').format(
                        election=election_data['name']
                    ),
                    required=False,
                    choices=[('', '')] + sorted(
                        [
                            (post['id'],
                             AREA_POST_DATA.shorten_post_label(
                                 election,
                                 post['label']
                             ))
                            for post in get_all_posts_cached(self.api, role)
                        ],
                        key=lambda t: t[1]
                    ),
                    widget=forms.Select(attrs={'class': 'post-select'}),
                )

        self.fields['constituency_' + election] = post_field

        # It seems to be common in elections around the world for
        # there to be different sets of parties that candidates can
        # stand for depending on, for example, where in the country
        # they're standing. (For example, in the UK General Election,
        # there is a different register of parties for Northern
        # Ireland and Great Britain constituencies.) We create a party
        # choice field for each such "party set" and make sure only
        # the appropriate one is shown, depending on the election and
        # selected constituency, using Javascript.
        specific_party_set_slug = None
        if hidden_post_widget:
            # Then the post can't be changed, so only add the
            # particular party set relevant for that post:
            post_id = kwargs['initial']['constituency_' + election]
            specific_party_set_slug = \
                AREA_POST_DATA.post_id_to_party_set(post_id)

        for party_set in PARTY_DATA.ALL_PARTY_SETS:
            if specific_party_set_slug and (party_set['slug'] != specific_party_set_slug):
                continue
            self.fields['party_' + party_set['slug'] + '_' + election] = \
                forms.ChoiceField(
                    label=_("Party in {election} ({party_set_name})").format(
                        election=election_data['name'],
                        party_set_name=party_set['name'],
                    ),
                    choices=PARTY_DATA.party_choices[party_set['slug']],
                    required=False,
                    widget=forms.Select(
                        attrs={
                            'class': 'party-select party-select-' + election
                        }
                    ),
                )

    source = forms.CharField(
        label=_(u"Source of information ({0})").format(
            settings.SOURCE_HINTS
        ),
        max_length=512,
        error_messages={
            'required': _('You must indicate how you know about this candidate')
        },
        widget=forms.TextInput(
            attrs={
                'required': 'required',
                'placeholder': _('How you know about this candidate')
            }
        )
    )

    def clean(self):
        cleaned_data = super(NewPersonForm, self).clean()
        return self.check_party_and_constituency_are_selected(cleaned_data)

class UpdatePersonForm(BasePersonForm):

    def __init__(self, *args, **kwargs):
        super(UpdatePersonForm, self).__init__(*args, **kwargs)

        # We should only need to actually go to the API for the first
        # time this form is loaded; it'll be cached indefinitely after
        # that, but still need the API object for the first time.
        api = create_popit_api_object()

        self.elections_with_fields = settings.ELECTIONS_CURRENT

        # The fields on this form depends on how many elections are
        # going on at the same time. (FIXME: this might be better done
        # with formsets?)

        for election, election_data in self.elections_with_fields:
            role = election_data['for_post_role']
            self.fields['standing_' + election] = \
                forms.ChoiceField(
                    label=_('Standing in %s') % election_data['name'],
                    choices=self.STANDING_CHOICES,
                    widget=forms.Select(attrs={'class': 'standing-select'}),
                )
            self.fields['constituency_' + election] = \
                forms.ChoiceField(
                    label=_('Constituency in %s') % election_data['name'],
                    required=False,
                    choices=[('', '')] + sorted(
                        [
                            (post['id'],
                             AREA_POST_DATA.shorten_post_label(
                                 election,
                                 post['label']
                             ))
                            for post in get_all_posts_cached(api, role)
                        ],
                        key=lambda t: t[1]
                    ),
                    widget=forms.Select(attrs={'class': 'post-select'}),
                )
            for party_set in PARTY_DATA.ALL_PARTY_SETS:
                self.fields['party_' + party_set['slug'] + '_' + election] = \
                    forms.ChoiceField(
                        label=_("Party in {election} ({party_set_name})").format(
                            election=election_data['name'],
                            party_set_name=party_set['name'],
                        ),
                        choices=PARTY_DATA.party_choices[party_set['slug']],
                        required=False,
                        widget=forms.Select(
                            attrs={
                                'class': 'party-select party-select-' + election
                            }
                        ),
                    )

    source = forms.CharField(
        label=_(u"Source of information for this change ({0})").format(
            settings.SOURCE_HINTS
        ),
        max_length=512,
        error_messages={
            'required': _('You must indicate how you know about this candidate')
        },
        widget=forms.TextInput(
            attrs={
                'required': 'required',
                'placeholder': _('How you know about this candidate')
            }
        )
    )

    def clean(self):
        cleaned_data = super(UpdatePersonForm, self).clean()
        return self.check_party_and_constituency_are_selected(cleaned_data)


class UserTermsAgreementForm(forms.Form):

    assigned_to_dc = forms.BooleanField(required=False)
    next_path = forms.CharField(
        max_length=512,
        widget=forms.HiddenInput(),
    )

    def clean_assigned_to_dc(self):
        assigned_to_dc = self.cleaned_data['assigned_to_dc']
        if not assigned_to_dc:
            message = _(
                "You can only edit data on {site_name} if you agree to "
                "this copyright assignment."
            ).format(site_name=Site.objects.get_current().name)
            raise ValidationError(message)
        return assigned_to_dc


class ToggleLockForm(forms.Form):
    lock = forms.BooleanField(
        required=False,
        widget=forms.HiddenInput()
    )
    post_id = forms.CharField(
        max_length=256,
        widget=forms.HiddenInput()
    )

    def clean_post_id(self):
        post_id = self.cleaned_data['post_id']
        # Use get_post_cached to check if this is a real post:
        try:
            api = create_popit_api_object()
            get_post_cached(api, post_id)
        except UnknownPostException:
            message = _('{0} was not a known post ID')
            raise ValidationError(message.format(post_id))
        return post_id


class ConstituencyRecordWinnerForm(forms.Form):
    person_id = forms.CharField(
        label=_('Person ID'),
        max_length=256,
        widget=forms.HiddenInput(),
    )
    source = forms.CharField(
        label=_(u"Source of information that they won"),
        max_length=512,
    )
