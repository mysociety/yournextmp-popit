from django.conf import settings
from django.db import models
from django.dispatch import receiver
from django.core.urlresolvers import reverse
from django.template.defaultfilters import slugify

from candidates.models import PopItPerson, person_added

class CachedCount(models.Model):
    """
    Fairly generic model for storing counts of various sorts.

    The object_id is used for linking through to the relevant URL.
    """

    count_type = models.CharField(blank=False, max_length=100, db_index=True)
    name = models.CharField(blank=False, max_length=100)
    count = models.IntegerField(blank=False, null=False)
    object_id = models.CharField(blank=True, max_length=100)
    election = models.CharField(blank=True, null=True, max_length=512)

    class Meta:
        ordering = ['-count', 'name']

    def __repr__(self):
        fmt = '<CachedCount: election={e} count_type={ct}, name={n}, count={c}, object_id={o}>'
        return fmt.format(
            e=repr(self.election),
            ct=repr(self.count_type),
            n=repr(self.name),
            c=repr(self.count),
            o=repr(self.object_id),
        )

    def __unicode__(self):
        return repr(self)

    @classmethod
    def increment_count(cls, election, count_type, object_id):
        """
        Increments the count of the object with the type of `count_type` and
        the id of `object_id`.  If this object does not exist, do nothing.
        """
        filters = {
            'election': election,
            'count_type': count_type,
            'object_id': object_id,
        }

        cls.objects.filter(**filters).update(count=models.F('count') + 1)

    @classmethod
    def get_attention_needed_queryset(cls):
        # FIXME: this should probably be a queryset method instead.
        current_election_slugs = [t[0] for t in settings.ELECTIONS_CURRENT]
        return cls.objects.filter(
            count_type='post',
            election__in=current_election_slugs
        ).order_by('count', '?')


@receiver(person_added, sender=PopItPerson)
def person_added_handler(sender, **kwargs):
    """
    Called when the `person_added` signal is sent, mainly from
    `candidates.update.create_person`.
    """

    data = kwargs['data']

    # constituency
    for election, standing_in_data in data['standing_in'].items():
        if standing_in_data:
            post_id = standing_in_data.get('post_id')
            CachedCount.increment_count(election, 'post', post_id)

    # party
    for election, party_membership_data in data['party_memberships'].items():
        if party_membership_data:
            party_id = party_membership_data['id']
            CachedCount.increment_count(election, 'party', party_id)
