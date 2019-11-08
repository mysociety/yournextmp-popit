# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django_webtest import WebTest
from nose.plugins.attrib import attr

import json
from mock import patch, Mock

from django.utils.six.moves.urllib_parse import urlsplit

import pygeocoder

from candidates.tests.factories import ParliamentaryChamberExtraFactory, ElectionFactory, AreaExtraFactory
from candidates.tests.settings import SettingsMixin
from elections.models import AreaType


def fake_geocode(q, **kwargs):
    if q.startswith('Nairobi'):
        return [
            Mock(coordinates=(-1.2921, 36.8219))
        ]
    else:
        raise pygeocoder.GeocoderError(
            "Fake geocoder doesn't know about '{0}'".format(q)
        )


def approx_equal(a, b, places=5):
    return int(round(a * 10**places)) == int(round(b * 10**places))


def fake_mapit_lookup(url):
    if url == 'http://info.mzalendo.com/mapit/point/4326/36.8219,-1.2921?type=DIS&generation=22':
        result = '''
{
    "5021":{
        "parent_area":null,
        "generation_high":3,
        "all_names":{

        },
        "id":5021,
        "codes":{
            "2017_coun":"47"
        },
        "name":"Nairobi",
        "country":"k",
        "type_name":"District",
        "generation_low":3,
        "country_name":"Kenya",
        "type":"DIS"
    }
}
'''
    else:
        result = '''
{}
'''
    return Mock(**{
        'json.return_value': json.loads(result),
        'status_code': 200
    })



@attr(country='kenya')
class KenyaTests(SettingsMixin, WebTest):
    def setUp(self):
        super(KenyaTests, self).setUp()

        org = ParliamentaryChamberExtraFactory.create()

        county_area_type = AreaType.objects.create(name='DIS')

        ElectionFactory.create(
            slug='election',
            name='Election',
            area_types=(county_area_type,),
            organization=org.base,
            current=True,
            election_date='2000-01-01'
        )

        AreaExtraFactory.create(
            base__identifier='county:47',
            base__name='Nairobi',
            type=county_area_type,
        )

    def test_front_page(self):
        # Check that our custom search form label is actually present
        response = self.app.get('/')
        self.assertContains(response, 'Enter your county or constituency:')

    @patch.object(pygeocoder.Geocoder, 'geocode', side_effect=fake_geocode)
    @patch('candidates.models.address.requests')
    def test_front_page_good_address_lookup(self, patched_requests, patched_geocode):
        patched_requests.get.side_effect = fake_mapit_lookup
        response = self.app.get('/')
        form = response.forms['form-address']
        form['address'] = 'Nairobi'
        response = form.submit()
        self.assertEqual(response.status_code, 302)
        split_location = urlsplit(response.location)
        self.assertEqual(
            split_location.path,
            '/areas/DIS-county:47/nairobi',
        )

    @patch.object(pygeocoder.Geocoder, 'geocode', side_effect=fake_geocode)
    @patch('candidates.models.address.requests')
    def test_front_page_bad_address_lookup(self, patched_requests, patched_geocode):
        patched_requests.get.side_effect = fake_mapit_lookup
        response = self.app.get('/')
        form = response.forms['form-address']
        form['address'] = 'Mah Nà Mah Nà'
        response = form.submit()
        self.assertEqual(response.status_code, 200)
        self.assertIn(
            'Failed to find a location for &#39;Mah Nà Mah Nà&#39;',
            response
        )
