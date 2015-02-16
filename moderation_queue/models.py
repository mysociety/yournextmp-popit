import datetime

from django.contrib.auth.models import User
from django.db import models


class QueuedImage(models.Model):

    APPROVED = 'approved'
    REJECTED = 'rejected'
    UNDECIDED = 'undecided'

    DECISION_CHOICES = (
        (APPROVED, 'Approved'),
        (REJECTED, 'Rejected'),
        (UNDECIDED, 'Undecided'),
    )

    public_domain = models.BooleanField(default=False)
    use_allowed_by_owner = models.BooleanField(default=False)
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

    created = models.DateTimeField(auto_now_add=True, default=datetime.datetime.now)
    updated = models.DateTimeField(auto_now=True, default=datetime.datetime.now)

    def __unicode__(self):
        message = u'Image uploaded by {user} of candidate {popit_person_id}'
        return message.format(
            user=self.user,
            popit_person_id=self.popit_person_id
        )
