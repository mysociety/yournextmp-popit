from django.db import models
from django.contrib.auth.models import User
from django.core.exceptions import ObjectDoesNotExist
from django.db.models.signals import post_save
from django.utils.translation import ugettext as _


class MaxPopItIds(models.Model):
    popit_collection_name = models.CharField(max_length=255)
    max_id = models.IntegerField(default=0)

    @classmethod
    def get_max_persons_id(cls):
        try:
            return cls.objects.get(popit_collection_name="persons").max_id
        except ObjectDoesNotExist:
            persons_max = cls(popit_collection_name="persons")
            persons_max.save()
            return persons_max.max_id

    @classmethod
    def update_max_persons_id(cls, max_id):
        max_persons, created = cls.objects.get_or_create(
            popit_collection_name="persons")
        if max_id > max_persons.max_id:
            max_persons.max_id = max_id
            max_persons.save()
        else:
            raise ValueError(_('given max_id is lower than the previous one ({'
                             '0} vs {1})').format(max_id, max_persons.max_id))


class LoggedAction(models.Model):
    '''A model for logging the actions of users on the site

    We record the changes that have been made to a person in PopIt in
    that person's 'versions' field, but is not much help for queries
    like "what has John Q User been doing on the site?". The
    LoggedAction model makes that kind of query easy, however, and
    should be helpful in tracking down both bugs and the actions of
    malicious users.'''

    user = models.ForeignKey(User, blank=True, null=True)
    action_type = models.CharField(max_length=64)
    popit_person_new_version = models.CharField(max_length=32)
    popit_person_id = models.CharField(max_length=256)
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)
    ip_address = models.CharField(max_length=50, blank=True, null=True)
    source = models.TextField()


class PersonRedirect(models.Model):
    '''This represents a redirection from one person ID to another

    This is typically used to redirect from the person that is deleted
    after two people are merged'''
    old_person_id = models.IntegerField()
    new_person_id = models.IntegerField()


class UserTermsAgreement(models.Model):
    user = models.OneToOneField(User, related_name='terms_agreement')
    assigned_to_dc = models.BooleanField(default=False)


def create_user_terms_agreement(sender, instance, created, **kwargs):
    if created:
        UserTermsAgreement.objects.create(user=instance)

post_save.connect(create_user_terms_agreement, sender=User)
