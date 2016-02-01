# -*- coding: utf-8 -*-

from __future__ import unicode_literals

from django.test import TestCase

from ..csv_helpers import list_to_csv

from . import factories


class CSVTests(TestCase):
    def setUp(self):
        # The second person's name (and party name) have diacritics in
        # them to test handling of Unicode when outputting to CSV.
        wmc_area_type = factories.AreaTypeFactory.create()
        gb_parties = factories.PartySetFactory.create(
            slug='gb', name='Great Britain'
        )
        ni_parties = factories.PartySetFactory.create(
            slug='ni', name='Northern Ireland'
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
        sinn_fein = factories.PartyExtraFactory.create(
            slug='party:39',
            base__name='Sinn Féin',
        )
        ni_parties.parties.add(sinn_fein.base)
        labour_party = factories.PartyExtraFactory.create(
            slug='party:53',
            base__name='Labour Party',
        )
        gb_parties.parties.add(labour_party.base)
        self.gb_person_extra = factories.PersonExtraFactory.create(
            base__id=2009,
            base__name='Tessa Jowell',
            base__honorific_suffix='DBE',
            base__honorific_prefix='Ms',
            base__email='jowell@example.com',
            base__gender='female',
        )
        self.ni_person_extra = factories.PersonExtraFactory.create(
            base__id=1953,
            base__name='Daithí McKay',
            base__gender='male',
        )
        camberwell_area_extra = factories.AreaExtraFactory.create(
            base__identifier='65913',
            base__name='Camberwell and Peckham',
            type=wmc_area_type,
        )
        camberwell_area_extra.base.other_identifiers.create(
            scheme='mapit-area-url',
            identifier='http://mapit.mysociety.org/area/65913',
        )
        camberwell_post_extra = factories.PostExtraFactory.create(
            elections=(self.election, self.earlier_election),
            base__organization=commons,
            base__area=camberwell_area_extra.base,
            slug='65913',
            base__label='Member of Parliament for Camberwell and Peckham',
            party_set=gb_parties,
        )
        north_antrim_area_extra = factories.AreaExtraFactory.create(
            base__identifier='66135',
            base__name='North Antrim',
            type=wmc_area_type,
        )
        north_antrim_area_extra.base.other_identifiers.create(
            scheme='mapit-area-url',
            identifier='http://mapit.mysociety.org/area/66135',
        )
        north_antrim_post_extra = factories.PostExtraFactory.create(
            elections=(self.election, self.earlier_election),
            base__organization=commons,
            base__area=north_antrim_area_extra.base,
            slug='66135',
            base__label='Member of Parliament for North Antrim',
            party_set=ni_parties,
        )
        factories.CandidacyExtraFactory.create(
            election=self.election,
            base__person=self.ni_person_extra.base,
            base__post=north_antrim_post_extra.base,
            base__on_behalf_of=sinn_fein.base
        )
        factories.CandidacyExtraFactory.create(
            election=self.earlier_election,
            base__person=self.ni_person_extra.base,
            base__post=north_antrim_post_extra.base,
            base__on_behalf_of=sinn_fein.base
        )
        factories.CandidacyExtraFactory.create(
            election=self.election,
            base__person=self.gb_person_extra.base,
            base__post=camberwell_post_extra.base,
            base__on_behalf_of=labour_party.base
        )
        factories.CandidacyExtraFactory.create(
            election=self.earlier_election,
            base__person=self.gb_person_extra.base,
            base__post=camberwell_post_extra.base,
            base__on_behalf_of=labour_party.base
        )

    def test_as_dict(self):
        person_dict = self.gb_person_extra.as_dict(self.election)
        self.assertEqual(len(person_dict), 26)
        self.assertEqual(person_dict['id'], 2009)

    def test_as_dict_2010(self):
        # Could do with a person example who changes constituency
        person_dict = self.gb_person_extra.as_dict(self.earlier_election)
        self.assertEqual(len(person_dict), 26)
        self.assertEqual(person_dict['id'], 2009)

    def test_csv_output(self):
        example_output = (
            b'id,name,honorific_prefix,honorific_suffix,gender,birth_date,election,party_id,party_name,post_id,post_label,mapit_url,elected,email,twitter_username,facebook_page_url,party_ppc_page_url,facebook_personal_url,homepage_url,wikipedia_url,linkedin_url,image_url,proxy_image_url_template,image_copyright,image_uploading_user,image_uploading_user_notes\r\n'
            b'2009,Tessa Jowell,Ms,DBE,female,,2015,party:53,Labour Party,65913,Camberwell and Peckham,http://mapit.mysociety.org/area/65913,,jowell@example.com,,,,,,,,,,,,\r\n'
            b'1953,Daith\xc3\xad McKay,,,male,,2015,party:39,Sinn F\xc3\xa9in,66135,North Antrim,http://mapit.mysociety.org/area/66135,,,,,,,,,,,,,,\r\n'
        ).decode('utf-8')
        self.assertEqual(
            list_to_csv(
                [
                    p.as_dict(self.election) for p in
                    (self.gb_person_extra, self.ni_person_extra)
                ]
            ),
            example_output,
        )
