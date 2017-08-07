# If you need to define any forms specific to this country's site, put
# those definitions here.

from __future__ import unicode_literals

from django import forms
from django.utils.translation import ugettext_lazy as _

from popolo.models import Area


class CountySelectorForm(forms.Form):

    county_id = forms.ModelChoiceField(
        label=_('Select your county'),
        empty_label='',
        to_field_name='identifier',
        queryset=Area.objects.filter(classification='County').order_by('name')
    )
