from django import forms

from .models import OfficialDocument

class UploadDocumentForm(forms.ModelForm):
    class Meta:
        model = OfficialDocument
        fields = (
            'election',
            'uploaded_file',
            'source_url',
            'post_id',
            'document_type',
        )

    post_id = forms.CharField(widget=forms.HiddenInput())
    election = forms.CharField(widget=forms.HiddenInput())
    document_type = forms.CharField(widget=forms.HiddenInput())
