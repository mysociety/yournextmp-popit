from __future__ import unicode_literals

from django.contrib.auth.models import User
from django.db import models

from popolo.models import Person
from candidates.models import OrganizationExtra

class ResultEvent(models.Model):

    class Meta:
        ordering = ['created']

    created = models.DateTimeField(auto_now_add=True)
    election = models.CharField(blank=True, null=True, max_length=512)
    winner = models.ForeignKey(Person)
    winner_person_name = models.CharField(blank=False, max_length=1024)
    post_id = models.CharField(blank=False, max_length=256)
    post_name = models.CharField(blank=True, null=True, max_length=1024)
    winner_party_id = models.CharField(blank=True, null=True, max_length=256)
    source = models.CharField(max_length=512)
    user = models.ForeignKey(User, blank=True, null=True)
    proxy_image_url_template = \
        models.CharField(blank=True, null=True, max_length=1024)
    parlparse_id = models.CharField(blank=True, null=True, max_length=256)

    @property
    def winner_party_name(self):
        return OrganizationExtra.objects \
            .select_related('base') \
            .get(
                slug=self.winner_party_id
            ).base.name
