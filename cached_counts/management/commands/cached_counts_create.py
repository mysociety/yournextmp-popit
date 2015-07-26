from collections import defaultdict
from optparse import make_option

from candidates.models import membership_covers_date
from candidates.popit import PopItApiMixin, get_all_posts
from candidates.election_specific import PARTY_DATA

from django.conf import settings
from django.core.management.base import BaseCommand

from cached_counts.models import CachedCount

class Command(PopItApiMixin, BaseCommand):

    option_list = BaseCommand.option_list + (
        make_option(
            '--delete-dissolved-parties',
            action='store_true',
            dest='delete_dissolved',
            help='Delete cached counts for any dissolved parties'
        ),
    )

    def add_or_update(self, obj):
        CachedCount.objects.update_or_create(
            election=obj['election'],
            object_id=obj['object_id'],
            count_type=obj['count_type'],
            defaults={
                'count': obj['count'],
                'name': obj['name'],
            }
        )

    def handle(self, **options):
        person_to_elections = defaultdict(list)
        election_to_people = defaultdict(set)
        for election, election_data in settings.ELECTIONS_BY_DATE:
            post_role = election_data['for_post_role']
            # We iterate over the posts twice, so just evaluate the
            # generator to a list before iterating:
            all_posts = list(
                get_all_posts(post_role, embed='membership.person')
            )
            all_parties = PARTY_DATA.party_id_to_name
            counts = {
                'candidates': 0,
                'parties': {
                    party_id: {'count': 0, 'party_name': name}
                    for party_id, name in all_parties.items()
                },
                'posts': {
                    str(p['id']): {'count': 0, 'post_label': p['label']}
                    for p in all_posts
                },
            }
            for post in all_posts:
                for m in post['memberships']:
                    candidate_role = election_data['candidate_membership_role']
                    if m.get('role') != candidate_role:
                        continue
                    person = m['person_id']
                    standing_in = person.get('standing_in') or {}
                    if not standing_in.get(election):
                        continue
                    if not membership_covers_date(m, election_data['election_date']):
                        continue
                    counts['candidates'] += 1
                    counts['posts'][post['id']]['count'] += 1
                    election_to_people[election].add(person['id'])
                    party = person['party_memberships'][election]
                    party_id = party['id']
                    counts['parties'].setdefault(
                        party_id,
                        {'count': 0, 'party_name': party['name']}
                    )
                    counts['parties'][party_id]['count'] += 1
                    person_to_elections[person['id']].append(
                        {
                            'election': election,
                            'election_data': election_data,
                            'party_id': party_id,
                        }
                    )
                    party_id

            # Posts
            for post_id, data in counts['posts'].items():
                obj = {
                    'election': election,
                    'count_type': 'post',
                    'name': data['post_label'],
                    'count': data['count'],
                    'object_id': post_id
                }
                self.add_or_update(obj)

            # Add or create objects in the database
            # Parties
            for party_id, data in counts['parties'].items():
                obj = {
                    'election': election,
                    'count_type': 'party',
                    'name': data['party_name'],
                    'count': data['count'],
                    'object_id': party_id

                }
                self.add_or_update(obj)

            # Set the total party count
            self.add_or_update({
                'election': election,
                'count_type': 'total',
                'name': 'total',
                'count': counts['candidates'],
                'object_id': election,
            })

        # Now we've been through all candidates for all elections, go
        # back through all the current elections to see if anyone stood
        # for a non-current election:

        for current_election, current_election_data in settings.ELECTIONS_CURRENT:
            standing_again_same_party_from = defaultdict(int)
            standing_again_different_party_from = defaultdict(int)
            new_candidates_from = defaultdict(int)
            standing_again_from = defaultdict(int)
            for person_id in election_to_people[election]:
                # Get their party in the current_election:
                current_party = None
                for d in person_to_elections[person_id]:
                    if current_election == d['election']:
                        current_party = d['party_id']
                # Now go through all non-current elections, and find
                # whether that person was in them:
                for d in person_to_elections[person_id]:
                    election = d['election']
                    election_data = d['election_data']
                    party_id = d['party_id']
                    if election_data['current']:
                        continue
                    standing_again_from[election] += 1
                    if party_id == current_party:
                        standing_again_same_party_from[election] += 1
                    else:
                        standing_again_different_party_from[election] += 1
            # Now work out how many new candidates there were with
            # respect to each of those previous elections.
            for election, election_data in settings.ELECTIONS_BY_DATE:
                if election_data['current']:
                    continue
                total_candidates = CachedCount.objects.get(
                    election=election,
                    count_type='total',
                    name='total'
                ).count
                new_candidates_from[election] = \
                    total_candidates - standing_again_from[election]
                # Now add all these relative totals to the database:
                for count_type, d in (
                        ('standing_again_same_party', standing_again_same_party_from),
                        ('standing_again_different_party', standing_again_different_party_from),
                        ('new_candidates', new_candidates_from),
                        ('standing_again', standing_again_from),
                ):
                    self.add_or_update({
                        'election': current_election,
                        'count_type': count_type,
                        'name': count_type,
                        # Possibly slightly abusing the object_id
                        # field to indicate the other election these
                        # counts are relative to:
                        'object_id': election,
                        'count': d[election],
                    })

        if options['delete_dissolved']:
            # Remove any parties that have dissolved but still might have
            # entries in the database:
            parties_in_database = set(
                CachedCount.objects.filter(count_type='party'). \
                    values_list('object_id', flat=True)
            )
            current_parties = set(
                PARTY_DATA.party_id_to_name.keys()
            )
            parties_to_remove = parties_in_database - current_parties
            CachedCount.objects.filter(
                count_type='party',
                object_id__in=parties_to_remove
            ).delete()
