from collections import defaultdict

from django.core.urlresolvers import reverse
from django.conf import settings
from django.http import HttpResponseRedirect

from slugify import slugify

from ..election_specific import AREA_POST_DATA, PARTY_DATA
from ..models import (
    PopItPerson, membership_covers_date
)

def get_redirect_to_post(election, post_data):
    short_post_label = AREA_POST_DATA.shorten_post_label(
        election, post_data['label']
    )
    return HttpResponseRedirect(
        reverse(
            'constituency',
            kwargs={
                'election': election,
                'post_id': post_data['id'],
                'ignored_slug': slugify(short_post_label),
            }
        )
    )

def get_party_people_for_election_from_memberships(
        election,
        party_id,
        memberships
):
    people = []
    election_data = settings.ELECTIONS[election]
    for membership in memberships:
        if not membership.get('role') == election_data['candidate_membership_role']:
            continue
        person = PopItPerson.create_from_dict(membership['person_id'])
        if person.party_memberships[election]['id'] != party_id:
            continue
        position_in_list = membership.get('party_list_position')
        if position_in_list:
            position_in_list = int(position_in_list)
        else:
            position_in_list = None
        people.append((position_in_list, person))
    people.sort(key=lambda t: (t[0] is None, t[0]))
    return people

def get_people_from_memberships(election_data, memberships):
    current_candidates = set()
    past_candidates = set()
    for membership in memberships:
        if not membership.get('role') == election_data['candidate_membership_role']:
            continue
        person = PopItPerson.create_from_dict(membership['person_id'])
        if membership_covers_date(
                membership,
                election_data['election_date']
        ):
            current_candidates.add(person)
        else:
            for other_election, other_election_data in settings.ELECTIONS_BY_DATE:
                if not other_election_data.get('use_for_candidate_suggestions'):
                    continue
                if membership_covers_date(
                        membership,
                        other_election_data['election_date'],
                ):
                    past_candidates.add(person)

    return current_candidates, past_candidates

def group_people_by_party(election, people, party_list=True, max_people=None):
    """Take a list of candidates and return them grouped by party

    This returns a tuple of the party_list boolean and a list of
    parties-and-people.

    The the parties-and-people list is a list of tuples; each tuple
    has two elements, the first of which is a dictionary with the
    party's ID and name, while the second is a list of people in that
    party.  The list of people for each party is sorted by their last
    names.

    The order of the tuples in the parties-and-people list is
    determined by the party_list parameter.  When party_list is True,
    the groups of parties are ordered by their names.  Otherwise
    (where there is typically one candidate per party), the groups
    will be ordered by the last name of the first candidate for each
    party."""

    # We need to build up this dictionary based on the embedded
    # memberships because PARTY_DATA.party_id_to_name doesn't include
    # now-dissolved parties...
    party_id_to_name = {}
    party_id_to_people = defaultdict(list)
    party_truncated = dict()
    election_data = settings.ELECTIONS[election]
    for person in people:
        if election in person.party_memberships:
            party_data = person.party_memberships[election]
        else:
            party_data = person.last_party
        position = None
        if election_data['party_lists_in_use']:
            position = person.standing_in[election].get('party_list_position')
        party_id = party_data['id']
        party_id_to_name[party_id] = party_data['name']
        party_id_to_people[party_id].append((position, person))
    for party_id, people_list in party_id_to_people.items():
        if election_data['party_lists_in_use']:
            # sort by party list position
            people_list.sort(key=lambda p: ( p[0] is None, p[0] ))
            """ only return the configured maximum number of people
-           for a party list """
            if max_people and len(people_list) > max_people:
                party_truncated[party_id] = len(people_list)
                del people_list[max_people:]
        else:
            people_list.sort(key=lambda p: p[1].last_name)
    try:
        result = [
            (
                {
                    'id': k,
                    'name': party_id_to_name[k],
                    'max_count': max_people,
                    'total_count': party_truncated.get(k)
                },
                # throw away the party list position data we
                # were only using for sorting
                [p[1] for p in v]
            )
            for k, v in party_id_to_people.items()
        ]
    except KeyError as ke:
        raise Exception(u"Unknown party: {0}".format(ke))
    if party_list:
        result.sort(key=lambda t: t[0]['name'])
    else:
        result.sort(key=lambda t: t[1][0].last_name)
    return {
        'party_lists_in_use': party_list,
        'parties_and_people': result
    }
