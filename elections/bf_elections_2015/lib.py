from candidates.static_data import (
    BaseMapItData, BasePartyData, BaseAreaPostData
)


class MapItData(BaseMapItData):
    pass


class PartyData(BasePartyData):
    def __init__(self):
        super(PartyData, self).__init__()
        self.ALL_PARTY_SETS = (
            {'slug': 'national', 'name': 'National'},
        )

    def party_data_to_party_sets(self, party_data):
        return ['national']


class AreaPostData(BaseAreaPostData):

    def area_to_post_group(self, area_data):
        return None

    def shorten_post_label(self, election, post_label):
        return post_label

    def post_id_to_post_group(self, election, post_id):
        return None

    def post_id_to_party_set(self, post_id):
        return 'national'
