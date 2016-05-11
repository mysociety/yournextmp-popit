# -*- coding: utf-8 -*-

from __future__ import unicode_literals

import re

from django import forms
from django.conf import settings
from django.contrib.sites.models import Site
from django.core.exceptions import ValidationError
from django.utils.translation import ugettext_lazy as _

from compat import StrippedCharField, StrippedEmailField, StrippedURLField
from elections.models import Election
from popolo.models import Organization, OtherName, Post

from .date_parsing import DateCharField
from .models import (
    PartySet, ExtraField, SimplePopoloField, ComplexPopoloField
)
from .models.address import check_address
from .twitter_api import get_twitter_user_id, TwitterAPITokenMissing


class AddressForm(forms.Form):
    address = StrippedCharField(
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
    person_id = StrippedCharField(
        label=_('Person ID'),
        max_length=256,
    )
    post_id = StrippedCharField(
        label=_('Post ID'),
        max_length=256,
    )


class CandidacyCreateForm(BaseCandidacyForm):
    source = StrippedCharField(
        label=_("Source of information that they're standing ({0})").format(
            settings.SOURCE_HINTS
        ),
        max_length=512,
    )


class CandidacyDeleteForm(BaseCandidacyForm):
    source = StrippedCharField(
        label=_("Information source for this change ({0})").format(
            settings.SOURCE_HINTS
        ),
        max_length=512,
    )


class BasePersonForm(forms.Form):

    def __init__(self, *args, **kwargs):
        super(BasePersonForm, self).__init__(*args, **kwargs)

        # Add any extra fields to the person form:
        for field in ExtraField.objects.all():
            if field.type == 'line':
                self.fields[field.key] = \
                    StrippedCharField(
                        label=_(field.label),
                        max_length=1024,
                        required=False,
                    )
            elif field.type == 'longer-text':
                self.fields[field.key] = \
                    StrippedCharField(
                        label=_(field.label),
                        required=False,
                        widget=forms.Textarea,
                    )
            elif field.type == 'url':
                self.fields[field.key] = \
                    StrippedURLField(
                        label=_(field.label),
                        max_length=256,
                        required=False,
                    )
            elif field.type == 'yesno':
                self.fields[field.key] = \
                    forms.ChoiceField(
                        label=_(field.label),
                        required=False,
                        # even though these are the same labels as STANDING_CHOICES
                        # the values of that are too specific for a generic field
                        # so we redefine them here.
                        choices=(
                            ('not-sure', _("Don’t Know")),
                            ('yes', _("Yes")),
                            ('no', _("No")),
                        )
                    )
            else:
                raise Exception(
                    "Unknown field type: {0}".format(field.type)
                )

        for field in SimplePopoloField.objects.all():
            opts = {
                'label': _(field.label),
                'required': field.required
            }

            if field.info_type_key == 'url':
                self.fields[field.name] = StrippedURLField(**opts)
            elif field.info_type_key == 'email':
                self.fields[field.name] = StrippedEmailField(**opts)
            elif field.name == 'birth_date' or field.name == 'death_date':
                self.fields[field.name] = DateCharField(**opts)
            else:
                self.fields[field.name] = StrippedCharField(**opts)

        for field in ComplexPopoloField.objects.all():
            opts = {
                'label': _(field.label),
                'required': False
            }

            if field.field_type == 'url':
                self.fields[field.name] = StrippedURLField(**opts)
            elif field.field_type == 'email':
                self.fields[field.name] = StrippedEmailField(**opts)
            else:
                self.fields[field.name] = StrippedCharField(**opts)

    STANDING_CHOICES = (
        ('not-sure', _("Don’t Know")),
        ('standing', _("Yes")),
        ('not-standing', _("No")),
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
        if username:
            try:
                user_id = get_twitter_user_id(username)
                if not user_id:
                    message = _("The Twitter account {screen_name} doesn't exist")
                    raise ValidationError(message.format(screen_name=username))
            except TwitterAPITokenMissing:
                # If there's no API token, we can't check the screen name,
                # but don't fail validation because the site owners
                # haven't set that up.
                return username
        return username

    def check_party_and_constituency_are_selected(self, cleaned_data):
        '''This is called by the clean method of subclasses'''

        for election_data in self.elections_with_fields:
            election = election_data.slug
            election_name = election_data.name

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
            if not Post.objects.filter(extra__slug=post_id).exists():
                message = _("An unknown post ID '{post_id}' was specified")
                raise forms.ValidationError(
                    message.format(post_id=post_id)
                )
            try:
                party_set = PartySet.objects.get(postextra__slug=post_id)
            except PartySet.DoesNotExist:
                message = _("Could not find parties for the post with ID "
                            "'{post_id}' in the {election}")
                raise forms.ValidationError(
                    message.format(post_id=post_id, election=election_name)
                )
            party_field = 'party_' + party_set.slug + '_' + election
            try:
                party_id = int(cleaned_data[party_field], 10)
            except ValueError:
                party_id = None
            if not Organization.objects.filter(
                    classification='Party', id=party_id).exists():
                message = _("You must specify a party for the {election}")
                raise forms.ValidationError(message.format(election=election_name))
        return cleaned_data


class NewPersonForm(BasePersonForm):

    def __init__(self, *args, **kwargs):
        from .election_specific import shorten_post_label
        election = kwargs.pop('election', None)
        hidden_post_widget = kwargs.pop('hidden_post_widget', None)
        super(NewPersonForm, self).__init__(*args, **kwargs)

        election_data = Election.objects.get_by_slug(election)

        standing_field_kwargs = {
            'label': _('Standing in %s') % election_data.name,
            'choices': self.STANDING_CHOICES,
        }
        if hidden_post_widget:
            standing_field_kwargs['widget'] = forms.HiddenInput()
        else:
            standing_field_kwargs['widget'] = forms.Select(attrs={'class': 'standing-select'})
        self.fields['standing_' + election] = \
            forms.ChoiceField(**standing_field_kwargs)

        self.elections_with_fields = [
            election_data
        ]


        post_field_kwargs = {
            'label': _("Post in the {election}").format(
                election=election_data.name
            ),
            'max_length': 256,
        }
        if hidden_post_widget:
            post_field_kwargs['widget'] = forms.HiddenInput()
            post_field = StrippedCharField(**post_field_kwargs)
        else:
            post_field = \
                forms.ChoiceField(
                    label=_('Post in the {election}').format(
                        election=election_data.name
                    ),
                    required=False,
                    choices=[('', '')] + sorted(
                        [
                            (post.extra.slug,
                             shorten_post_label(post.label))
                            for post in Post.objects.select_related('extra').filter(extra__elections__slug=election)
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
        specific_party_set = None
        if hidden_post_widget:
            # Then the post can't be changed, so only add the
            # particular party set relevant for that post:
            post_id = kwargs['initial']['constituency_' + election]
            specific_party_set = PartySet.objects.get(
                postextra__slug=post_id
            )

        for party_set in PartySet.objects.all():
            if specific_party_set and (party_set.slug != specific_party_set.slug):
                continue
            self.fields['party_' + party_set.slug + '_' + election] = \
                forms.ChoiceField(
                    label=_("Party in {election}").format(
                        election=election_data.name,
                    ),
                    choices=party_set.party_choices(),
                    required=False,
                    widget=forms.Select(
                        attrs={
                            'class': 'party-select party-select-' + election
                        }
                    ),
                )
            if election_data.party_lists_in_use:
                # Then add a field to enter the position on the party list
                # as an integer:
                field_name = 'party_list_position_' + party_set.slug + \
                    '_' + election
                self.fields[field_name] = forms.IntegerField(
                    label=_("Position in party list ('1' for first, '2' for second, etc.)"),
                    min_value=1,
                    required=False,
                    widget=forms.NumberInput(
                        attrs={
                            'class': 'party-position party-position-' + election
                        }
                    )
                )

    source = StrippedCharField(
        label=_("Source of information ({0})").format(
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
        from .election_specific import shorten_post_label
        super(UpdatePersonForm, self).__init__(*args, **kwargs)

        self.elections_with_fields = Election.objects.current().by_date()

        # The fields on this form depends on how many elections are
        # going on at the same time. (FIXME: this might be better done
        # with formsets?)

        for election_data in self.elections_with_fields:
            election = election_data.slug
            self.fields['standing_' + election] = \
                forms.ChoiceField(
                    label=_('Standing in %s') % election_data.name,
                    choices=self.STANDING_CHOICES,
                    widget=forms.Select(attrs={'class': 'standing-select'}),
                )
            self.fields['constituency_' + election] = \
                forms.ChoiceField(
                    label=_('Constituency in %s') % election_data.name,
                    required=False,
                    choices=[('', '')] + sorted(
                        [
                            (post.extra.slug,
                             shorten_post_label(post.label))
                            for post in Post.objects.select_related('extra').filter(extra__elections__slug=election)
                        ],
                        key=lambda t: t[1]
                    ),
                    widget=forms.Select(attrs={'class': 'post-select'}),
                )
            for party_set in PartySet.objects.all():
                self.fields['party_' + party_set.slug + '_' + election] = \
                    forms.ChoiceField(
                        label=_("Party in {election} ({party_set_name})").format(
                            election=election_data.name,
                            party_set_name=party_set.name,
                        ),
                        choices=party_set.party_choices(),
                        required=False,
                        widget=forms.Select(
                            attrs={
                                'class': 'party-select party-select-' + election
                            }
                        ),
                    )
                if election_data.party_lists_in_use:
                    # Then add a field to enter the position on the party list
                    # as an integer:
                    field_name = 'party_list_position_' + party_set.slug + \
                        '_' + election
                    self.fields[field_name] = forms.IntegerField(
                        label=_("Position in party list ('1' for first, '2' for second, etc.)"),
                        min_value=1,
                        required=False,
                        widget=forms.NumberInput(
                            attrs={
                                'class': 'party-position party-position-' + election
                            }
                        )
                    )

    source = StrippedCharField(
        label=_("Source of information for this change ({0})").format(
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
    next_path = StrippedCharField(
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
    post_id = StrippedCharField(
        max_length=256,
        widget=forms.HiddenInput()
    )


class ConstituencyRecordWinnerForm(forms.Form):
    person_id = StrippedCharField(
        label=_('Person ID'),
        max_length=256,
        widget=forms.HiddenInput(),
    )
    source = StrippedCharField(
        label=_("Source of information that they won"),
        max_length=512,
    )


class OtherNameForm(forms.ModelForm):
    class Meta:
        model = OtherName
        fields = ('name', 'note', 'start_date', 'end_date')
        labels = {
        }
        help_texts = {
            'start_date': _('(Optional) The date from which this name would be used'),
            'end_date': _('(Optional) The date when this name stopped being used'),
        }
    source = StrippedCharField(
        label=_("Source"),
        help_text=_(
            "Please indicate how you know that this is a valid alternative name"
        ),
        max_length=512,
    )
