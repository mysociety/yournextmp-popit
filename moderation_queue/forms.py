from __future__ import unicode_literals

import re

from django import forms
from django.core.exceptions import ValidationError
from django.utils.translation import ugettext as _

from .models import QueuedImage, CopyrightOptions

class UploadPersonPhotoForm(forms.ModelForm):

    class Meta:
        model = QueuedImage
        fields = [
            'image', 'why_allowed',
            'justification_for_use', 'person', 'decision'
        ]
        widgets = {
            'person': forms.HiddenInput(),
            'decision': forms.HiddenInput(),
            'why_allowed': forms.RadioSelect(),
            'justification_for_use': forms.Textarea(
                attrs={'rows': 1, 'columns': 72}
            )
        }

    def clean(self):
        cleaned_data = super(UploadPersonPhotoForm, self).clean()
        justification_for_use = cleaned_data.get(
            'justification_for_use', ''
        ).strip()
        why_allowed = cleaned_data.get('why_allowed')
        if why_allowed == 'other' and not justification_for_use:
            message = _("If you checked 'Other' then you must provide a "
                "justification for why we can use it.")
            raise ValidationError(message)
        return cleaned_data


class PhotoReviewForm(forms.Form):

    queued_image_id = forms.IntegerField(
        required=True,
        widget=forms.HiddenInput(),
    )
    x_min = forms.IntegerField(min_value=0)
    x_max = forms.IntegerField(min_value=1)
    y_min = forms.IntegerField(min_value=0)
    y_max = forms.IntegerField(min_value=1)
    decision = forms.ChoiceField(choices=QueuedImage.DECISION_CHOICES)
    make_primary = forms.BooleanField(required=False)
    rejection_reason = forms.CharField(
        widget=forms.Textarea(),
        required=False
    )
    justification_for_use = forms.CharField(
        widget=forms.Textarea(),
        required=False
    )
    moderator_why_allowed = forms.ChoiceField(
        choices=CopyrightOptions.WHY_ALLOWED_CHOICES
    )
