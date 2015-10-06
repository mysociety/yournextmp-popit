# -*- coding: utf-8 -*-

from datetime import date

ELECTIONS = {
    # Party primaries for the chamber of deputies:
    'council-member-2015': {
        'for_post_role': 'Council Member',
        'candidate_membership_role': 'Candidate',
        'winner_membership_role': 'Candidate',
        'election_date': date(2015, 11, 3),
        'candidacy_start_date': date(2015, 6, 22),
        'name': 'City Council Election',
        'current': True,
        'use_for_candidate_suggestions': False,
        'party_membership_start_date': date(2015, 6, 22),
        'party_membership_end_date': date(9999, 12, 31),
        'party_lists_in_use': False,
        'organization_id': 'saint-paul-city-council',
        'organization_name': 'Saint Paul City Council',
        'post_id_format': 'ocd-division,country:us,state:mn,place:st_paul,ward:{area_id}',
        'ocd_division': 'ocd-division/country:us/state:mn/place:st_paul/ward',
        'mapit_types': ['WARD'],
        'mapit_generation': 1,
    },
    'school-board-2015': {
        'for_post_role': 'School Board Member',
        'candidate_membership_role': 'Candidate',
        'winner_membership_role': 'Candidate',
        'election_date': date(2015, 11, 3),
        'candidacy_start_date': date(2015, 6, 22),
        'name': 'School Board Election',
        'current': True,
        'use_for_candidate_suggestions': False,
        'party_membership_start_date': date(2015, 6, 22),
        'party_membership_end_date': date(9999, 12, 31),
        'party_lists_in_use': False,
        'mapit_types': ['MUN'],
        'mapit_generation': 1,
        'organization_id': 'saint-paul-school-board',
        'organization_name': 'Saint Paul School Board',
        'post_id_format': 'ocd-division,country:us,state:mn,place:st_paul',
        'ocd_division': 'ocd-division/country:us/state:mn/place:st_paul',
    },
}

MAPIT_BASE_URL = ''
# OCD_BOUNDARIES_URL = 'http://127.0.0.1:8001'
OCD_BOUNDARIES_URL = 'http://ocd.datamade.us'

