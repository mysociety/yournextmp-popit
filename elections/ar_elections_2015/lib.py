# -*- coding: utf-8 -*-

from django.utils.text import slugify

from candidates.static_data import (
    BaseMapItData, BasePartyData, BaseAreaPostData
)


class MapItData(BaseMapItData):
    pass


def index_lambda(sequence, predicate):
    for i, item in enumerate(sequence):
        if predicate(item):
            return i
    return -1

def move_to_front(l, predicate):
    i = index_lambda(l, lambda x: predicate(x))
    l.insert(0, l.pop(i))


PARTY_SET_NAMES = [
    u"Buenos Aires",
    u"Capital Federal",
    u"Catamarca",
    u"Chaco",
    u"Chubut",
    u"Córdoba",
    u"Corrientes",
    u"Entre Ríos",
    u"Formosa",
    u"Jujuy",
    u"La Pampa",
    u"La Rioja",
    u"Mendoza",
    u"Misiones",
    u"Nacional",
    u"Neuquén",
    u"Río Negro",
    u"Salta",
    u"San Juan",
    u"San Luis",
    u"Santa Cruz",
    u"Santa Fe",
    u"Santiago Del Estero",
    u"Tierra del Fuego",
    u"Tucumán",
]
PARTY_SET_SLUG_TO_NAME = {
    slugify(n): n for n in PARTY_SET_NAMES
}
PARTY_SET_NAME_TO_SLUG = {
    v: k for k, v in PARTY_SET_SLUG_TO_NAME.items()
}

AREA_NAME_TO_PARTY_SET_NAME = {
    u"BUENOS AIRES": u"Buenos Aires",
    u"CIUDAD AUTONOMA DE BUENOS AIRES": u"Capital Federal",
    u"CATAMARCA": u"Catamarca",
    u"CHACO": u"Chaco",
    u"CHUBUT": u"Chubut",
    u"CORDOBA": u"Córdoba",
    u"CORRIENTES": u"Corrientes",
    u"ENTRE RIOS": u"Entre Ríos",
    u"FORMOSA": u"Formosa",
    u"JUJUY": u"Jujuy",
    u"LA PAMPA": u"La Pampa",
    u"LA RIOJA": u"La Rioja",
    u"MENDOZA": u"Mendoza",
    u"MISIONES": u"Misiones",
    u"Argentina": u"Nacional",
    u"NEUQUEN": u"Neuquén",
    u"RIO NEGRO": u"Río Negro",
    u"SALTA": u"Salta",
    u"SAN JUAN": u"San Juan",
    u"SAN LUIS": u"San Luis",
    u"SANTA CRUZ": u"Santa Cruz",
    u"SANTA FE": u"Santa Fe",
    u"SANTIAGO DEL ESTERO": u"Santiago Del Estero",
    u"TIERRA DEL FUEGO, ANTARTIDA E ISLAS DEL ATLANTICO SUR": u"Tierra del Fuego",
    u"TUCUMAN": u"Tucumán",
}

class PartyData(BasePartyData):

    def __init__(self):
        super(PartyData, self).__init__()
        self.ALL_PARTY_SETS = tuple(
            {'slug': k, 'name': v}
            for k, v in PARTY_SET_SLUG_TO_NAME.items()
        )

    def party_data_to_party_sets(self, party_data):
        territory = party_data.get('territory')
        # If it's a non-territorial party, or a national party, they
        # should be available in all party sets:
        if territory is None or territory == 'Nacional':
            return PARTY_SET_SLUG_TO_NAME.keys()
        return [PARTY_SET_NAME_TO_SLUG[territory]]

    def sort_parties_in_place(self, parties):
        parties.sort(key=lambda p: p[1].lower())
        # Then we need 'unknown' and 'not listed' at the top:
        move_to_front(parties, lambda x: x[0] == 'not-listed')
        move_to_front(parties, lambda x: x[0] == 'unknown')


class AreaPostData(BaseAreaPostData):

    def __init__(self, *args, **kwargs):
        super(AreaPostData, self).__init__(*args, **kwargs)
        self.ALL_POSSIBLE_POST_GROUPS = [None]

    def area_to_post_group(self, area_data):
        return None

    def post_id_to_party_set(self, post_id):
        area = self.areas_by_post_id.get(post_id, None)
        if area is None:
            return 'nacional'
        party_set_name = AREA_NAME_TO_PARTY_SET_NAME[area['name']]
        party_set_slug = PARTY_SET_NAME_TO_SLUG[party_set_name]
        return party_set_slug

    def post_id_to_post_group(self, election, post_id):
        return None

    def shorten_post_label(self, election, post_label):
        return post_label

    def party_to_possible_post_groups(self, party_data):
        return (None,)
