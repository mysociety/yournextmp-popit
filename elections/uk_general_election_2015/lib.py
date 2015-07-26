import re

from candidates.static_data import (
    BaseMapItData, BasePartyData, BaseAreaPostData
)

class MapItData(BaseMapItData):
    pass


class PartyData(BasePartyData):

    def __init__(self):
        super(PartyData, self).__init__()
        self.ALL_PARTY_SETS = (
            {'slug': 'gb', 'name': 'Great Britain'},
            {'slug': 'ni', 'name': 'Northern Ireland'},
        )

    def party_data_to_party_sets(self, party_data):
        register = {
            'Great Britain': 'gb',
            'Northern Ireland': 'ni',
        }.get(party_data.get('register'))
        if register:
            return [register]
        else:
            # There are some pseudo-parties, like 'Independent' or
            # 'Speaker seeking re-election' which won't have a register,
            # so we add them to all party sets.
            return ['gb', 'ni']


class AreaPostData(BaseAreaPostData):

    def __init__(self, *args, **kwargs):
        super(AreaPostData, self).__init__(*args, **kwargs)
        self.ALL_POSSIBLE_POST_GROUPS = [
            'England', 'Northern Ireland', 'Scotland', 'Wales'
        ]

    def area_to_post_group(self, area_data):
        return area_data['country_name']

    def post_id_to_party_set(self, post_id):
        area = self.areas_by_post_id.get(post_id, None)
        if area is None:
            return None
        if area['country_name'] == 'Northern Ireland':
            return 'ni'
        elif area['country_name'] in ('England', 'Scotland', 'Wales'):
            return 'gb'
        return None

    def post_id_to_post_group(self, election, post_id):
        # In the UK, the post IDs are the same as MapIt IDs,
        # so just look it up from the MapIt data:
        areas_by_id = self.mapit_data.areas_by_id[('WMC', 22)]
        area = areas_by_id.get(post_id)
        return area['country_name']

    def shorten_post_label(self, election, post_label):
        return re.sub(r'^Member of Parliament for ', '', post_label)

    def party_to_possible_post_groups(self, party_data):
        register = party_data.get('register')
        if register == 'Northern Ireland':
            return ('Northern Ireland',)
        elif register == 'Great Britain':
            return ('England', 'Scotland', 'Wales')
        else:
            return ('England', 'Northern Ireland', 'Scotland', 'Wales')

EXTRA_CSV_ROW_FIELDS = [
    'gss_code',
    'parlparse_id',
    'theyworkforyou_url',
    'party_ec_id',
]

def get_extra_csv_values(person, election, mapit_data):
    theyworkforyou_url = None
    parlparse_id = person.get_identifier('uk.org.publicwhip')
    if parlparse_id:
        m = re.search(r'^uk.org.publicwhip/person/(\d+)$', parlparse_id)
        if not m:
            message = "Malformed parlparse ID found {0}"
            raise Exception, message.format(parlparse_id)
        parlparse_person_id = m.group(1)
        theyworkforyou_url = 'http://www.theyworkforyou.com/mp/{0}'.format(
            parlparse_person_id
        )
    party_ec_id = person.parties[election].get('electoral_commission_id', '')

    return {
        'gss_code': mapit_data.areas_by_id[('WMC', 22)][
            person.standing_in[election]['post_id']
        ]['codes']['gss'],
        'parlparse_id': parlparse_id,
        'theyworkforyou_url': theyworkforyou_url,
        'party_ec_id': party_ec_id
    }
