import os

from django.db import models
from django.utils.translation import ugettext_lazy as _

from django_extensions.db.models import TimeStampedModel

DOCUMENT_UPLOADERS_GROUP_NAME = "Document Uploaders"


def document_file_name(instance, filename):
    return os.path.join(
        "official_documents",
        instance.post_id,
        filename,
    )


class OfficialDocument(TimeStampedModel):
    NOMINATION_PAPER = 'Nomination paper'

    DOCUMENT_TYPES = (
        (NOMINATION_PAPER, _('Nomination paper'), _('Nomination papers')),
    )

    election = models.CharField(blank=True, null=True, max_length=512)
    document_type = models.CharField(
        blank=False,
        choices=[ (d[0], d[1]) for d in DOCUMENT_TYPES ],
        max_length=100)
    uploaded_file = models.FileField(
        upload_to=document_file_name, max_length=800)
    post_id = models.CharField(blank=False, max_length=50)
    source_url = models.URLField(blank=True,
        help_text=_("The page that links to this document"),
        max_length=1000,
    )

    def __unicode__(self):
        return u"{0} ({1})".format(
            self.post_id,
            self.source_url,
        )

    @models.permalink
    def get_absolute_url(self):
        return ('uploaded_document_view', (), {'pk': self.pk})
