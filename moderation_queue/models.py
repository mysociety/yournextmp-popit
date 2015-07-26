import datetime

from django.contrib.auth.models import User
from django.core.urlresolvers import reverse
from django.db import models
from django.utils.translation import ugettext_lazy as _


PHOTO_REVIEWERS_GROUP_NAME = 'Photo Reviewers'


class QueuedImage(models.Model):

    APPROVED = 'approved'
    REJECTED = 'rejected'
    UNDECIDED = 'undecided'
    IGNORE = 'ignore'

    DECISION_CHOICES = (
        (APPROVED, _('Approved')),
        (REJECTED, _('Rejected')),
        (UNDECIDED, _('Undecided')),
        (IGNORE, _('Ignore')),
    )

    PUBLIC_DOMAIN = 'public-domain'
    COPYRIGHT_ASSIGNED = 'copyright-assigned'
    PROFILE_PHOTO = 'profile-photo'
    OTHER = 'other'

    WHY_ALLOWED_CHOICES = (
        (PUBLIC_DOMAIN,
         _("This photograph is free of any copyright restrictions")),
        (COPYRIGHT_ASSIGNED,
         _("I own copyright of this photo and I assign the copyright "
         "to Democracy Club Limited in return for it being displayed "
         "on YourNextMP")),
        (PROFILE_PHOTO,
         _("This is the candidate's public profile photo from social "
         "media (e.g. Twitter, Facebook) or their official campaign "
         "page")),
        (OTHER,
         _("Other")),
    )

    why_allowed = models.CharField(
        max_length=64,
        choices=WHY_ALLOWED_CHOICES,
        default=OTHER,
    )
    justification_for_use = models.TextField(blank=True)
    decision = models.CharField(
        max_length=32,
        choices=DECISION_CHOICES,
        default=UNDECIDED
    )
    image = models.ImageField(
        upload_to='queued-images/%Y/%m/%d',
        max_length=512,
    )
    popit_person_id = models.CharField(max_length=256)
    user = models.ForeignKey(User, blank=True, null=True)

    crop_min_x = models.IntegerField(blank=True, null=True)
    crop_min_y = models.IntegerField(blank=True, null=True)
    crop_max_x = models.IntegerField(blank=True, null=True)
    crop_max_y = models.IntegerField(blank=True, null=True)

    face_detection_tried = models.BooleanField(default=False)

    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)

    def __unicode__(self):
        message = _(u'Image uploaded by {user} of candidate {popit_person_id}')
        return message.format(
            user=self.user,
            popit_person_id=self.popit_person_id
        )

    def get_absolute_url(self):
        return reverse('photo-review', kwargs={'queued_image_id': self.id})

    @property
    def has_crop_bounds(self):
        crop_fields = ['crop_min_x', 'crop_min_y', 'crop_max_x', 'crop_max_y']
        return not any(getattr(self, c) is None for c in crop_fields)
