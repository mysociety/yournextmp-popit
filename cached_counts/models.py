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

    class Meta:
        ordering = ['-count', 'name']

    @classmethod
    def total_2015(cls):
        print cls.objects.get(name="total_2015")
        return cls.objects.get(name="total_2015").count

    @property
    def object_url(self):
        if self.count_type == "constituency":
            return reverse('constituency', kwargs={
                'mapit_area_id': self.object_id,
                'ignored_slug': slugify(self.name)
            })

    @classmethod
    def increment_count(cls, count_type, object_id):
        """
        Increments the count of the object with the type of `count_type` and
        the id of `object_id`.  If this object does not exist, do nothing.
        """
        filters = {
            'count_type': count_type,
            'object_id': object_id,
        }

        cls.objects.filter(**filters).update(count=models.F('count') + 1)


@receiver(person_added, sender=PopItPerson)
def person_added_handler(sender, **kwargs):
    """
    Called when the `person_added` signal is sent, mainly from
    `candidates.update.create_person`.
    """

    data = kwargs['data']

    # constituency
    constituency_url = data['standing_in'].get('2015', {}).get('mapit_url')
    constituency_id = constituency_url.split('/')[-1]
    CachedCount.increment_count('constituency', constituency_id)

    # party
    party_id = data['party_memberships'].get('2015', {}).get('id')
    CachedCount.increment_count('party', party_id)
