from candidates.popit import PopItApiMixin, popit_unwrap_pagination

from django.conf import settings
from django.core.management.base import BaseCommand

from ...models import PopItPerson, membership_covers_date

from candidates.views.version_data import get_change_metadata

def get_parlparse_id(person_data):
    parlparse_identifiers = [
        i for i in
        person_data.get('identifiers', [])
        if i['scheme'] == 'uk.org.publicwhip'
    ]
    if len(parlparse_identifiers) > 1:
        message = "Found multiple parlparse IDs for {0}"
        raise Exception(message.format(person_data['id']))
    if parlparse_identifiers:
        return parlparse_identifiers[0]['identifier']
    else:
        return None


class Command(PopItApiMixin, BaseCommand):

    def existing_candidate_same_party(self, cons_id, party_id):
        cons = self.api.posts(cons_id).get(embed='membership.person')['result']
        for cons_membership in cons['memberships']:
            candidate_role = settings.ELECTIONS['2015']
            if cons_membership['role'] != candidate_role:
                continue
            if not membership_covers_date(
                    cons_membership,
                    settings.ELECTIONS['2015']['election_date'],
            ):
                continue
            person_party_membership = cons_membership['person_id']['party_memberships']
            party_id_2015 = person_party_membership.get('2015', {}).get('id')
            if party_id == party_id_2015:
                return True
        return False

    def handle(self, **options):

        for person_popit_data in popit_unwrap_pagination(
                self.api.persons,
                per_page=100
        ):
            # Exclude anyone who doesn't have a parlparse ID; this is
            # more or less the incumbents (by-elections causing the
            # "more or less" bit.)
            if not get_parlparse_id(person_popit_data):
                continue

            if '2015' in person_popit_data['standing_in']:
                print "We already have 2015 information for", person_popit_data['name']
                continue

            person = PopItPerson.create_from_dict(person_popit_data)

            print "Considering person:", person.name

            cons_id = person.standing_in['2010']['post_id']
            party_id = person.party_memberships['2010']['id']
            party_name = person.party_memberships['2010']['name']
            cons_url = 'https://yournextmp.com/constituency/{0}'.format(cons_id)

            # We're now considering marking the candidate as standing
            # again in the same consituency as in 2010. Check that
            # there's not another candidate from their party already
            # marked as standing in that consituency.

            if self.existing_candidate_same_party(cons_id, party_id):
                msg = u"There was already a candidate for {0} in {1} - skipping"
                print msg.format(party_name, cons_url).format('utf-8')
                continue

            # Now it should be safe to update the candidate and set
            # them as standing in 2015.

            person.standing_in['2015'] = person.standing_in['2010']
            person.party_memberships['2015'] = person.party_memberships['2010']

            person.record_version(
                get_change_metadata(
                    None,
                    "Assuming that incumbents we don't have definite information on yet are standing again",
                )
            )
            person.save_to_popit(self.api)
            person.invalidate_cache_entries()

            message = u"Marked an incumbent ({name} - {party}) as standing again in {cons_url}"
            print message.format(
                name=person.name,
                party=party_name,
                cons_url=cons_url,
            ).encode('utf-8')
