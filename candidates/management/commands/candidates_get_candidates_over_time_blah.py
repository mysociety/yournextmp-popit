from collections import defaultdict
import csv
import re

from candidates.popit import PopItApiMixin, popit_unwrap_pagination

from django.core.management.base import BaseCommand

class Command(PopItApiMixin, BaseCommand):

    def handle(self, **options):
        date_count = defaultdict(int)
        total_candidates = 0
        twitter_usernames = 0
        email_addresses = 0
        both_twitter_and_email = 0
        neither_twitter_nor_email = 0
        for person in popit_unwrap_pagination(
                self.api.persons,
                per_page=100
        ):
            if not person.get('standing_in'):
                continue
            if not person['standing_in'].get('2015'):
                continue
            total_candidates += 1
            have_twitter = False
            have_email = False
            if person['versions'][0]['data']['twitter_username']:
                have_twitter = True
                twitter_usernames += 1
            if person['versions'][0]['data']['email']:
                have_email = True
                email_addresses += 1
            if have_email and have_twitter:
                both_twitter_and_email += 1
            elif not (have_email or have_twitter):
                neither_twitter_nor_email += 1
            versions = person.get('versions')
            for version in reversed(versions):
                standing_in = version['data'].get('standing_in', {})
                if standing_in.get('2015'):
                    date_str = re.sub(r'T.*', '', version['timestamp'])
                    date_count[date_str] += 1
                    break
        print "Candidates with Twitter usernames: {0}%".format((100 * twitter_usernames) / total_candidates)
        print "Candidates with email addresses: {0}%".format((100 * email_addresses) / total_candidates)
        print "Candidates with neither Twitter nor email: {0}%".format((100 * neither_twitter_nor_email) / total_candidates)
        print "Candidates with both Twitter and email: {0}%".format((100 * both_twitter_and_email) / total_candidates)
        cumulative = 0
        with open('candidates-over-time', 'wb') as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow(['Date', 'New Candidates', 'Cumulative Candidates'])
            for row in sorted(date_count.items()):
                cumulative += row[1]
                row = list(row) + [cumulative]
                writer.writerow(row)
