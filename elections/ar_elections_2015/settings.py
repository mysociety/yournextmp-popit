# -*- coding: utf-8 -*-

from datetime import date

ELECTIONS = {
    # Party primaries for the chamber of deputies:
    'diputados-argentina-paso-2015': {
        'for_post_role': 'Diputado Nacional',
        'candidate_membership_role': 'Primary Candidate',
        'winner_membership_role': 'Candidate',
        'election_date': date(2015, 8, 9),
        'candidacy_start_date': date(2015, 6, 22),
        'name': 'Diputados Nacionales PASO 2015',
        'current': True,
        'use_for_candidate_suggestions': False,
        'party_membership_start_date': date(2015, 6, 22),
        'party_membership_end_date': date(9999, 12, 31),
        'party_lists_in_use': False,
        'mapit_types': ['PRV'],
        'mapit_generation': 1,
        'organization_id': 'hcdn',
        'organization_name': 'Cámara de Diputados',
        'post_id_format': 'dip-{area_id}',
        'show_official_documents': False,
    },
    # Party primaries for governors of provinces
    'gobernadores-argentina-paso-2015': {
        'for_post_role': 'Gobernador',
        'candidate_membership_role': 'Primary Candidate',
        'winner_membership_role': 'Candidate',
        'election_date': date(2015, 8, 9),
        'candidacy_start_date': date(2015, 6, 22),
        'name': 'Gobernador PASO 2015',
        'current': True,
        'party_membership_start_date': date(2015, 6, 22),
        'party_membership_end_date': date(9999, 12, 31),
        'party_lists_in_use': False,
        'mapit_types': ['PRV'],
        'mapit_generation': 1,
        'organization_id': 'gobernador',
        'organization_name': 'Gobernador',
        'post_id_format': 'gob-{area_id}',
        'show_official_documents': False,
    },
    # Party primaries for national senators
    'senadores-argentina-paso-2015': {
        'for_post_role': 'Senador Nacional',
        'candidate_membership_role': 'Primary Candidate',
        'winner_membership_role': 'Candidate',
        'election_date': date(2015, 8, 9),
        'candidacy_start_date': date(2015, 6, 22),
        'name': 'Senadores Nacionales PASO 2015',
        'current': True,
        'party_membership_start_date': date(2015, 6, 22),
        'party_membership_end_date': date(9999, 12, 31),
        'party_lists_in_use': False,
        'mapit_types': ['PRV'],
        'mapit_generation': 1,
        'organization_id': 'hcsn',
        'organization_name': 'Senado de la Nación',
        'post_id_format': 'sen-{area_id}',
        'show_official_documents': False,
    },
    # Presidential candidates
    'presidentes-argentina-paso-2015': {
        'for_post_role': 'Presidente',
        'candidate_membership_role': 'Primary Candidate',
        'winner_membership_role': 'Candidate',
        'election_date': date(2015, 8, 9),
        'candidacy_start_date': date(2015, 6, 22),
        'organization_id': 'pen',
        'organization_name': 'Presidencia de la Nación Argentina',
        'name': 'Presidentes PASO 2015',
        'current': True,
        'party_membership_start_date': date(2015, 6, 22),
        'party_membership_end_date': date(9999, 12, 31),
        'party_lists_in_use': False,
        'mapit_types': ['NAT'], # The national level...
        'mapit_generation': 1,
        # There's only one such post:
        'post_id_format': 'presidente',
        'show_official_documents': False,
    },
}

MAPIT_BASE_URL = 'http://argentina.mapit.staging.mysociety.org/'
