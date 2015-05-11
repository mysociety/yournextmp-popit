from django.contrib.auth.models import User
from django.db import models

from candidates.static_data import MapItData, PartyData

class ResultEvent(models.Model):

    class Meta:
        ordering = ['created']

    created = models.DateTimeField(auto_now_add=True)
    winner_popit_person_id = models.CharField(blank=False, max_length=256)
    winner_person_name = models.CharField(blank=False, max_length=1024)
    post_id = models.CharField(blank=False, max_length=256)
    winner_party_id = models.CharField(blank=True, null=True, max_length=256)
    source = models.CharField(max_length=512)
    user = models.ForeignKey(User, blank=True, null=True)
    proxy_image_url_template = \
        models.CharField(blank=True, null=True, max_length=1024)
    parlparse_id = models.CharField(blank=True, null=True, max_length=256)

    @property
    def winner_party_name(self):
        return PartyData.party_id_to_name.get(self.winner_party_id)

    @property
    def constituency_name(self):
        return MapItData.constituencies_2010[self.post_id]['name']

    @classmethod
    def create_from_popit_person(cls, popit_person, election, source, user):
        kwargs = {
            'winner_popit_person_id': popit_person.id,
            'winner_person_name': popit_person.name,
            'post_id': popit_person.standing_in[election]['post_id'],
            'winner_party_id': popit_person.party_memberships[election]['id'],
            'source': source,
            'user': user,
            'parlparse_id': popit_person.get_identifier('uk.org.publicwhip')
        }
        if popit_person.proxy_image:
            kwargs['proxy_image_url_template'] = \
                '{base}/{{width}}/{{height}}.{{extension}}'.format(
                    base=popit_person.proxy_image
                )
        return ResultEvent.objects.create(**kwargs)
