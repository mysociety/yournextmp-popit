# -*- coding: utf-8 -*-

from __future__ import unicode_literals

from mock import patch, Mock

from datetime import date, timedelta

from nose.plugins.attrib import attr
from django_webtest import WebTest

from candidates.tests.factories import (
    AreaTypeFactory, ElectionFactory, PostExtraFactory,
    ParliamentaryChamberFactory, ParliamentaryChamberExtraFactory,
    PartySetFactory, AreaExtraFactory
)
from elections.models import Election
from elections.uk_general_election_2015.tests.mapit_postcode_results \
    import se240ag_result, sw1a1aa_result

from compat import text_type


def fake_requests_for_mapit(url):
    """Return reduced MapIt output for some known URLs"""
    if url == 'http://mapit.mysociety.org/postcode/sw1a1aa':
        status_code = 200
        json_result = sw1a1aa_result
    elif url == 'http://mapit.mysociety.org/postcode/se240ag':
        status_code = 200
        json_result = se240ag_result
    elif url == 'http://mapit.mysociety.org/postcode/cb28rq':
        status_code = 404
        json_result = {
            "code": 404,
            "error": "No Postcode matches the given query."
        }
    elif url == 'http://mapit.mysociety.org/postcode/foobar':
        status_code = 400
        json_result = {
            "code": 400,
            "error": "Postcode 'FOOBAR' is not valid."
        }
    else:
        raise Exception("URL that hasn't been mocked yet: " + url)
    return Mock(**{
        'json.return_value': json_result,
        'status_code': status_code
    })

@attr(country='uk')
@patch('elections.uk_general_election_2015.mapit.requests')
class TestUpcomingElectionsAPI(WebTest):
    def setUp(self):
        election = Election.objects.get(slug='2015')
        wmc_area_type = election.area_types.get(name='WMC')
        gb_parties = PartySetFactory.create(slug='gb', name='Great Britain')
        commons = ParliamentaryChamberFactory.create()
        area_extra = AreaExtraFactory.create(
            base__name="Dulwich and West Norwood",
            type=wmc_area_type,
        )
        self.area = area_extra.base
        PostExtraFactory.create(
            elections=(election,),
            base__organization=commons,
            slug='65808',
            base__label='Member of Parliament for Dulwich and West Norwood',
            party_set=gb_parties,
            base__area=area_extra.base,
        )

    def test_empty_results(self, mock_requests):
        mock_requests.get.side_effect = fake_requests_for_mapit
        response = self.app.get('/upcoming-elections/?postcode=SW1A+1AA')

        output = response.json
        self.assertEqual(output, [])

    def test_results_for_past_elections(self, mock_requests):
        mock_requests.get.side_effect = fake_requests_for_mapit
        response = self.app.get('/upcoming-elections/?postcode=SE24+0AG')

        output = response.json
        self.assertEqual(output, [])

    def test_results_for_upcoming_elections(self, mock_requests):
        one_day = timedelta(days=1)
        future_date = date.today() + one_day
        london_assembly = ParliamentaryChamberExtraFactory.create(
            slug='london-assembly', base__name='London Assembly'
        )
        lac_area_type = AreaTypeFactory.create(name='LAC')
        gla_area_type = AreaTypeFactory.create(name='GLA')
        area_extra_lac = AreaExtraFactory.create(
            base__identifier='11822',
            base__name="Dulwich and West Norwood",
            type=lac_area_type,
        )
        area_extra_gla = AreaExtraFactory.create(
            base__identifier='2247',
            base__name='Greater London Authority',
            type=gla_area_type,
        )
        election_lac = ElectionFactory.create(
            slug='gb-gla-2016-05-05-c',
            organization=london_assembly.base,
            name='2016 London Assembly Election (Constituencies)',
            election_date=future_date.isoformat(),
            area_types=(lac_area_type,),
        )
        election_gla = ElectionFactory.create(
            slug='gb-gla-2016-05-05-a',
            organization=london_assembly.base,
            name='2016 London Assembly Election (Additional)',
            election_date=future_date.isoformat(),
            area_types=(gla_area_type,),
        )
        PostExtraFactory.create(
            elections=(election_lac,),
            base__area=area_extra_lac.base,
            base__organization=london_assembly.base,
            slug='11822',
            base__label='Assembly Member for Lambeth and Southwark',
        )
        PostExtraFactory.create(
            elections=(election_gla,),
            base__area=area_extra_gla.base,
            base__organization=london_assembly.base,
            slug='2247',
            base__label='Assembly Member',
        )

        mock_requests.get.side_effect = fake_requests_for_mapit
        response = self.app.get('/upcoming-elections/?postcode=SE24+0AG')

        output = response.json
        self.assertEqual(len(output), 2)

        self.maxDiff = None
        expected = [
            {
                'organization': 'London Assembly',
                'election_date': text_type(future_date.isoformat()),
                'election_name': '2016 London Assembly Election (Constituencies)',
                'post_name': 'Assembly Member for Lambeth and Southwark',
                'area': {
                    'identifier': '11822',
                    'type': 'LAC',
                    'name': 'Dulwich and West Norwood'
                }
            },
            {
                'organization': 'London Assembly',
                'election_date': text_type(future_date.isoformat()),
                'election_name': '2016 London Assembly Election (Additional)',
                'post_name': 'Assembly Member',
                'area': {
                    'identifier': '2247',
                    'type': 'GLA',
                    'name': 'Greater London Authority'
                }
            },
        ]

        self.assertEqual(expected, output)
