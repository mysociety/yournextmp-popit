import re
import os
import json

from candidates.static_data import (
    BaseMapItData, BasePartyData, BaseAreaPostData
)

class MapItData(BaseMapItData):
    pass


class PartyData(BasePartyData):

    def __init__(self):
        super(PartyData, self).__init__()
        self.ALL_PARTY_SETS = (
            {'slug': 'st-paul', 'name': 'Saint Paul, Minnesota'},
        )

    def party_data_to_party_sets(self, party_data):
        return ['st-paul']

class AreaPostData(BaseAreaPostData):

    def shorten_post_label(self, election, post_label):
        return re.sub(r'^Council Member for ', '', post_label)

    def area_to_post_group(self, area_data):
        return area_data['country_name']

    def post_id_to_party_set(self, post_id):
        return 'st-paul'


