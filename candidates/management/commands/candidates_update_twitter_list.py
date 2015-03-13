import os
import csv

import twitter

from django.conf import settings
from django.core.management.base import BaseCommand

from candidates.popit import PopItApiMixin, popit_unwrap_pagination


class Command(PopItApiMixin, BaseCommand):
    def handle(self, **options):
        consumer_key = getattr(settings, 'TWITTER_KEY', None)
        consumer_secret = getattr(settings, 'TWITTER_SECRET', None)
        access_token_key = getattr(settings, 'TWITTER_TOKEN', None)
        access_token_secret = getattr(settings, 'TWITTER_TOKEN_SECRET', None)
        self.list_id = getattr(settings, 'TWITTER_LIST_ID', None)
        self.list_slug = getattr(settings, 'TWITTER_LIST_SLUG', None)

        if not all((
            consumer_key,
            consumer_secret,
            access_token_key,
            access_token_secret,
            self.list_id,
            self.list_slug)):
            raise ValueError('Twitter auth details not found in settings')

        self.api = twitter.Api(
            consumer_key=settings.TWITTER_KEY,
            consumer_secret=settings.TWITTER_SECRET,
            access_token_key=settings.TWITTER_TOKEN,
            access_token_secret=settings.TWITTER_TOKEN_SECRET,
        )

        self.existing_members = set(
            self.api.GetListMembers(self.list_id, self.list_slug))
        self.new_members = self.get_all_people() - self.existing_members
        self.new_members = list(self.new_members)
        self.update_list()

    def update_list(self):
        chunk_size = 50
        chunks = [self.new_members[x:x + chunk_size]
            for x in xrange(0, len(self.new_members), chunk_size)]

        for chunk in chunks:
            try:
                self.api.CreateListsMember(
                    self.list_id,
                    self.list_slug,
                    screen_name=chunk)
            except twitter.error.TwitterError, e:
                print "BAD USER:", chunk, e

    def get_from_csv(self):
        csv_path = os.path.join(settings.MEDIA_ROOT, 'candidates.csv')
        if not os.path.exists(csv_path):
            raise IOError("candidates.csv doesn't exist")

        with open(csv_path) as csv_file:
            csv_reader = csv.DictReader(csv_file)
            for line in csv_reader:
                if line['twitter_username']:
                    self.existing_people.add(line['twitter_username'])

    def get_from_popit(self):
        for person_dict in popit_unwrap_pagination(self.api.persons,
                            embed="membership.organization", per_page=100):
            if person_dict.get('standing_in', {}).get('2015'):
                for contact_point in person_dict['contact_details']:
                    if contact_point['type'] == "twitter":
                        self.existing_people.add(contact_point['value'])

    def get_all_people(self):
        self.existing_people = set()
        try:
            self.get_from_csv()
        except IOError:
            self.get_from_popit()
        return self.existing_people
