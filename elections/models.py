from __future__ import unicode_literals

from django.db import models
from django.shortcuts import get_object_or_404
from collections import defaultdict
from popolo.models import Organization

from compat import python_2_unicode_compatible


class ElectionQuerySet(models.QuerySet):
    def current(self, current=True):
        return self.filter(current=current)

    def get_by_slug(self, election):
        return get_object_or_404(self, slug=election)

    def by_date(self):
        return self.order_by(
            'election_date'
        )

class ElectionManager(models.Manager):
    def elections_for_area_generations(self):
        generations = defaultdict(list)
        for election in self.current():
            for area_type in election.area_types.all():
                area_tuple = (area_type.name, election.area_generation)
                generations[area_tuple].append(election)

        return generations


# FIXME: shouldn't AreaType also have the MapIt generation?
# FIXME: at the moment name is a code (like WMC); ideally that would
# be a code field and the name field would be "Westminster Consituency"
@python_2_unicode_compatible
class AreaType(models.Model):
    name = models.CharField(max_length=128)
    source = models.CharField(max_length=128, blank=True,
                              help_text="e.g MapIt")

    def __str__(self):
        return self.name

    def area_choices(self):
        return self.areas.all() \
            .order_by('base__name') \
            .values_list('id', 'base__name')


@python_2_unicode_compatible
class Election(models.Model):
    slug = models.CharField(max_length=128, unique=True)
    for_post_role = models.CharField(max_length=128)
    winner_membership_role = \
        models.CharField(max_length=128, null=True, blank=True)
    candidate_membership_role = models.CharField(max_length=128)
    election_date = models.DateField()
    name = models.CharField(max_length=128)
    current = models.BooleanField()
    use_for_candidate_suggestions = models.BooleanField(default=False)
    area_types = models.ManyToManyField(AreaType)
    area_generation = models.CharField(max_length=128, blank=True)
    organization = models.ForeignKey(Organization, null=True, blank=True)
    post_id_format = models.CharField(max_length=128, blank=True)
    party_lists_in_use = models.BooleanField(default=False)
    default_party_list_members_to_show = models.IntegerField(default=0)
    show_official_documents = models.BooleanField(default=False)
    ocd_division = models.CharField(max_length=250, blank=True)

    description = models.CharField(max_length=500, blank=True)

    objects = ElectionManager.from_queryset(ElectionQuerySet)()

    def __str__(self):
        return self.name
