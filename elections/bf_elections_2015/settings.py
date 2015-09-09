# -*- coding: utf-8 -*-

from datetime import date

ELECTIONS = {
    'pres-2015': {
        'current': True,
        'for_post_role': u'Président du Faso',
        'candidate_membership_role': u'Candidat',
        'winner_membership_role': None,
        'election_date': date(2015, 10, 11),
        'candidacy_start_date': date(2010, 11, 22),
        'organization_id': 'presidence',
        'organization_name': 'Présidence',
        'party_membership_start_date': date(2010, 11, 22),
        'party_membership_end_date': date(9999, 12, 31),
        'name': u'Elections Présidentielles de 2015',
        'mapit_types': ['NATIONAL'],
        'mapit_generation': 2,
        'post_id_format': 'president',
    },
    'nat-2015': {
        'current': True,
        'for_post_role': u'Député National',
        'candidate_membership_role': u'Candidat',
        'winner_membership_role': None,
        'election_date': date(2015, 10, 11),
        'candidacy_start_date': date(2012, 12, 3),
        'organization_id': 'assemblee-nationale',
        'organization_name': 'Assemblée nationale',
        'party_membership_start_date': date(2012, 12, 3),
        'party_membership_end_date': date(9999, 12, 31),
        'name': u'Elections Législative de 2015',
        'mapit_types': ['NATIONAL'],
        'mapit_generation': 2,
        'post_id_format': 'nat-{area_id}'
    },
    'prv-2015': {
        'current': True,
        'for_post_role': u'Député Provincial',
        'candidate_membership_role': u'Candidat',
        'winner_membership_role': None,
        'election_date': date(2015, 10, 11),
        'candidacy_start_date': date(2012, 12, 3),
        'organization_id': 'assemblee-nationale',
        'organization_name': 'Assemblée nationale',
        'party_membership_start_date': date(2012, 12, 3),
        'party_membership_end_date': date(9999, 12, 31),
        'name': u'Elections Législative de 2015',
        'mapit_types': ['PROVINCE'],
        'mapit_generation': 2,
        'post_id_format': 'prv-{area_id}'
    },
}

MAPIT_BASE_URL = 'http://international.mapit.mysociety.org/'

AREAS_TO_ALWAYS_RETURN = [
    {
        'area_type_code': 'NATIONAL',
        'area_id': 0,
    }
]
