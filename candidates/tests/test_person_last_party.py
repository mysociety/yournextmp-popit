from __future__ import unicode_literals

from django.test import TestCase

from . import factories

class TestPersonLastParty(TestCase):

    def setUp(self):
        wmc_area_type = factories.AreaTypeFactory.create()
        gb_parties = factories.PartySetFactory.create(
            slug='gb', name='Great Britain'
        )
        commons = factories.ParliamentaryChamberFactory.create()
        self.election = factories.ElectionFactory.create(
            slug='2015',
            name='2015 General Election',
            area_types=(wmc_area_type,)
        )
        self.earlier_election = factories.EarlierElectionFactory.create(
            slug='2010',
            name='2010 General Election',
            area_types=(wmc_area_type,)
        )
        factories.PartyExtraFactory.reset_sequence()
        factories.PartyFactory.reset_sequence()
        self.parties = {}
        for i in range(0, 4):
            party_extra = factories.PartyExtraFactory.create()
            gb_parties.parties.add(party_extra.base)
            self.parties[party_extra.slug] = party_extra
        self.post_extra = factories.PostExtraFactory.create(
            elections=(self.election,),
            base__organization=commons,
            slug='65808',
            base__label='Member of Parliament for Dulwich and West Norwood',
            party_set=gb_parties,
        )

    def test_both_elections(self):
        person_extra = factories.PersonExtraFactory.create(
            base__id=1234,
            base__name='John Doe',
        )
        factories.CandidacyExtraFactory.create(
            election=self.election,
            base__person=person_extra.base,
            base__post=self.post_extra.base,
            base__on_behalf_of=self.parties['party:53'].base,
        )
        factories.CandidacyExtraFactory.create(
            election=self.earlier_election,
            base__person=person_extra.base,
            base__post=self.post_extra.base,
            base__on_behalf_of=self.parties['party:90'].base,
        )
        self.assertEqual(
            person_extra.last_party(),
            self.parties['party:53'].base
        )

    def test_only_earlier(self):
        person_extra = factories.PersonExtraFactory.create(
            base__id=1234,
            base__name='John Doe',
        )
        factories.CandidacyExtraFactory.create(
            election=self.earlier_election,
            base__person=person_extra.base,
            base__post=self.post_extra.base,
            base__on_behalf_of=self.parties['party:90'].base,
        )
        self.assertEqual(
            person_extra.last_party(),
            self.parties['party:90'].base
        )

    def test_only_later(self):
        person_extra = factories.PersonExtraFactory.create(
            base__id=1234,
            base__name='John Doe',
        )
        factories.CandidacyExtraFactory.create(
            election=self.election,
            base__person=person_extra.base,
            base__post=self.post_extra.base,
            base__on_behalf_of=self.parties['party:53'].base,
        )
        self.assertEqual(
            person_extra.last_party(),
            self.parties['party:53'].base
        )
