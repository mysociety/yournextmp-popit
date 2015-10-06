from datetime import date

ELECTIONS = {
    '2010': {
        'for_post_role': 'Member of Parliament',
        'candidate_membership_role': 'Candidate',
        'winner_membership_role': None,
        'election_date': date(2010, 5, 6),
        'candidacy_start_date': date(2005, 5, 6),
        'organization_id': 'commons',
        'name': '2010 General Election',
        'current': False,
        'use_for_candidate_suggestions': True,
        'party_membership_start_date': date(2005, 5, 6),
        'party_membership_end_date': date(2010, 5, 6),
        'party_lists_in_use': False,
        'mapit_types': ['WMC'],
        'mapit_generation': 22,
        'post_id_format': '{area_id}',
        'show_official_documents': False,
    },
    '2015': {
        'for_post_role': 'Member of Parliament',
        'candidate_membership_role': 'Candidate',
        'winner_membership_role': None,
        'election_date': date(2015, 5, 7),
        'candidacy_start_date': date(2010, 5, 7),
        'organization_id': 'commons',
        'name': '2015 General Election',
        'current': True,
        'party_membership_start_date': date(2010, 5, 7),
        'party_membership_end_date': date(9999, 12, 31),
        'party_lists_in_use': False,
        'mapit_types': ['WMC'],
        'mapit_generation': 22,
        'post_id_format': '{area_id}',
        'show_official_documents': True,
    }
}

MAPIT_BASE_URL = 'http://mapit.mysociety.org/'
