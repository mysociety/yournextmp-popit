# -*- coding: utf-8 -*-

from __future__ import unicode_literals

import re

from django_webtest import WebTest

from candidates.models import PartySet
from .auth import TestUserMixin

from .factories import (
    AreaTypeFactory, ElectionFactory, EarlierElectionFactory,
    PostFactory, PostExtraFactory, ParliamentaryChamberFactory,
    PersonExtraFactory, CandidacyExtraFactory, PartyExtraFactory,
    PartyFactory, MembershipFactory, AreaExtraFactory, PartySetFactory
)

class TestAreasOfTypeView(TestUserMixin, WebTest):

    def setUp(self):
        wmc_area_type = AreaTypeFactory.create()
        gb_parties = PartySetFactory.create(slug='gb', name='Great Britain')
        commons = ParliamentaryChamberFactory.create()
        election = ElectionFactory.create(
            slug='2015',
            name='2015 General Election',
            area_types=(wmc_area_type,),
            organization=commons
        )
        dulwich_area_extra = AreaExtraFactory.create(
            base__identifier='65808',
            base__name='Dulwich and West Norwood',
            type=wmc_area_type,
        )
        post_extra = PostExtraFactory.create(
            elections=(election,),
            base__organization=commons,
            base__area=dulwich_area_extra.base,
            slug='65808',
            base__label='Member of Parliament for Dulwich and West Norwood',
            party_set=gb_parties,
        )
        person_extra = PersonExtraFactory.create(
            base__id='2009',
            base__name='Tessa Jowell'
        )
        PartyFactory.reset_sequence()
        party_extra = PartyExtraFactory.create()
        gb_parties.parties.add(party_extra.base)
        CandidacyExtraFactory.create(
            election=election,
            base__person=person_extra.base,
            base__post=post_extra.base,
            base__on_behalf_of=party_extra.base
            )

        aldershot_area_extra = AreaExtraFactory.create(
            base__identifier='65730',
            type=wmc_area_type,
        )
        PostExtraFactory.create(
            elections=(election,),
            base__area=aldershot_area_extra.base,
            base__organization=commons,
            slug='65730',
            base__label='Member of Parliament for Aldershot',
            party_set=gb_parties,
        )
        camberwell_area_extra = AreaExtraFactory.create(
            base__identifier='65913',
            type=wmc_area_type,
        )
        PostExtraFactory.create(
            elections=(election,),
            base__area=camberwell_area_extra.base,
            base__organization=commons,
            slug='65913',
            candidates_locked=True,
            base__label='Member of Parliament for Camberwell and Peckham',
            party_set=gb_parties,
        )

    def test_any_areas_of_type_page_without_login(self):
        response = self.app.get('/areas-of-type/WMC/')
        self.assertEqual(response.status_code, 200)

        self.assertTrue(
            re.search(
                r'''(?msx)
  <a\s+href="/areas/WMC-65808/dulwich-and-west-norwood">
  Dulwich\s+and\s+West\s+Norwood</a>''',
                response.text
            )
        )

    def test_get_malformed_url(self):
        response = self.app.get(
            '/areas-of-type/3243452345/invalid',
            expect_errors=True
        )
        self.assertEqual(response.status_code, 404)


    def test_get_non_existent(self):
        response = self.app.get(
            '/areas-of-type/AAA/',
            expect_errors=True
        )
        self.assertEqual(response.status_code, 404)
