# -*- coding: utf-8 -*-

from __future__ import unicode_literals

import json
from mock import patch, Mock

from django.utils.six.moves.urllib_parse import urlsplit

from django_webtest import WebTest
from nose.plugins.attrib import attr
import pygeocoder

from candidates.models import PartySet
from candidates.tests.factories import PostExtraFactory, AreaExtraFactory
from elections.models import AreaType, Election
from popolo.models import Organization


def fake_geocode(q, **kwargs):
    if q.startswith('631 Snelling Ave S, Saint Paul, MN'):
        return [
            Mock(coordinates=(44.9225785, -93.1674214))
        ]
    if q.startswith('Empire State Building, New York'):
        return [
            Mock(coordinates=(40.7484405, -73.98566439999999))
        ]
    else:
        raise pygeocoder.GeocoderError(
            "Fake geocoder doesn't know about '{0}'".format(q)
        )

def approx_equal(a, b, places=5):
    return int(round(a * 10**places)) == int(round(b * 10**places))


def fake_represent_boundaries(url, params):
    lat, lon = [float(n) for n in params['contains'].split(',')]
    if approx_equal(lat, 44.9225785) and approx_equal(lon, -93.1674214):
        result = '''
{
    "meta": {
        "limit": 20,
        "next": null,
        "offset": 0,
        "previous": null,
        "related": {
            "centroids_url": "/boundaries/centroid?contains=44.9225785,-93.1674214",
            "shapes_url": "/boundaries/shape?contains=44.9225785,-93.1674214",
            "simple_shapes_url": "/boundaries/simple_shape?contains=44.9225785,-93.1674214"
        },
        "total_count": 3
    },
    "objects": [
        {
            "boundary_set_name": "Saint Paul Precinct",
            "external_id": "ocd-division/country:us/state:mn/place:st_paul/ward:3/precinct:9",
            "name": "Ward 3, Precinct 9",
            "related": {
                "boundary_set_url": "/boundary-sets/st-paul-precincts/"
            },
            "url": "/boundaries/st-paul-precincts/ward-3-precinct-9/"
        },
        {
            "boundary_set_name": "Saint Paul",
            "external_id": "ocd-division/country:us/state:mn/place:st_paul",
            "name": "Saint Paul, Minnesota",
            "related": {
                "boundary_set_url": "/boundary-sets/st-paul-municipal/"
            },
            "url": "/boundaries/st-paul-municipal/saint-paul-minnesota/"
        },
        {
            "boundary_set_name": "Saint Paul Ward",
            "external_id": "ocd-division/country:us/state:mn/place:st_paul/ward:3",
            "name": "Ward 3",
            "related": {
                "boundary_set_url": "/boundary-sets/st-paul-wards/"
            },
            "url": "/boundaries/st-paul-wards/ward-3/"
        }
    ]
}
'''
    elif approx_equal(lat, 40.7484405) and approx_equal(lon, -73.98566439999999):
        result = '''
{
    "meta": {
        "limit": 20,
        "next": null,
        "offset": 0,
        "previous": null,
        "related": {
            "centroids_url": "/boundaries/centroid?contains=40.7484405,-73.98566439999999",
            "shapes_url": "/boundaries/shape?contains=40.7484405,-73.98566439999999",
            "simple_shapes_url": "/boundaries/simple_shape?contains=40.7484405,-73.98566439999999"
        },
        "total_count": 1
    },
    "objects": [
        {
            "boundary_set_name": "New York City Council District",
            "external_id": "ocd-division/country:us/state:ny/place:new_york/council_district:4",
            "name": "Council District 4",
            "related": {
                "boundary_set_url": "/boundary-sets/nyc-council-districts/"
            },
            "url": "/boundaries/nyc-council-districts/council-district-4/"
        }
    ]
}
'''
    else:
        result = '''
{
    "meta": {
        "limit": 20,
        "next": null,
        "offset": 0,
        "previous": null,
        "total_count": 0
    },
    "objects": []
}
'''
    return Mock(**{
        'json.return_value': json.loads(result),
        'status_code': 200
    })



@attr(country='st_paul')
class StPaulTests(WebTest):
    def setUp(self):
        election_school = Election.objects.get(slug='school-board-2015')
        election_council = Election.objects.get(slug='council-member-2015')
        ward_area_type = AreaType.objects.get(name='WARD')
        muni_area_type = AreaType.objects.get(name='MUNI')
        party_set = PartySet.objects.create(slug='st-paul')
        org_school = Organization.objects.get(
            extra__slug='saint-paul-school-board')
        org_city_council = Organization.objects.get(
            extra__slug='saint-paul-city-council')
        school_area_extra = AreaExtraFactory.create(
            base__identifier='ocd-division/country:us/state:mn/place:st_paul',
            base__name='Saint Paul',
            type=muni_area_type,
        )
        PostExtraFactory.create(
            elections=(election_school,),
            base__organization=org_school,
            slug='ocd-division,country:us,state:mn,place:st_paul',
            base__label='School Board Member for Saint Paul',
            party_set=party_set,
            base__area=school_area_extra.base,
        )
        ward3_area_extra = AreaExtraFactory.create(
            base__identifier='ocd-division/country:us/state:mn/place:st_paul/ward:3',
            base__name='Ward 3',
            type=ward_area_type,
        )
        PostExtraFactory.create(
            elections=(election_council,),
            base__organization=org_city_council,
            slug='ocd-division,country:us,state:mn,place:st_paul,ward:3',
            base__label='Council Member for Ward 3',
            party_set=party_set,
            base__area=ward3_area_extra.base,
        )

    def test_posts_page(self):
        response = self.app.get('/posts')
        with open('foo.html', 'w') as f:
            f.write(str(response))
        self.assertIn(
            '<h2>City Council Election</h2>',
            response,
        )
        self.assertIn(
            '<a href="/election/council-member-2015/post/ocd-division,country:us,state:mn,place:st_paul,ward:3/ward-3">Council Member for Ward 3</a>',
            response,
        )
        self.assertIn(
            '<h2>School Board Election</h2>',
            response,
        )
        self.assertIn(
            '<a href="/election/school-board-2015/post/ocd-division,country:us,state:mn,place:st_paul/school-board-member-for-saint-paul">School Board Member for Saint Paul</a>',
            response,
        )

    @patch.object(pygeocoder.Geocoder, 'geocode', side_effect=fake_geocode)
    @patch('elections.st_paul_municipal_2015.views.frontpage.requests')
    def test_front_page_good_address_lookup(self, patched_requests, patched_geocode):
        patched_requests.get.side_effect = fake_represent_boundaries
        response = self.app.get('/')
        form = response.forms['form-address']
        form['address'] = '631 Snelling Ave S, Saint Paul, MN'
        response = form.submit()
        self.assertEqual(response.status_code, 302)
        split_location = urlsplit(response.location)
        self.assertEqual(
            split_location.path,
            '/areas/ocd-division,country:us,state:mn,place:st_paul;ocd-division,country:us,state:mn,place:st_paul,ward:3',
        )

    @patch.object(pygeocoder.Geocoder, 'geocode', side_effect=fake_geocode)
    @patch('elections.st_paul_municipal_2015.views.frontpage.requests')
    def test_front_page_bad_address_lookup(self, patched_requests, patched_geocode):
        patched_requests.get.side_effect = fake_represent_boundaries
        response = self.app.get('/')
        form = response.forms['form-address']
        form['address'] = 'Mah Nà Mah Nà'
        response = form.submit()
        self.assertEqual(response.status_code, 200)
        self.assertIn(
            'Failed to find a location for &#39;Mah Nà Mah Nà&#39;',
            response
        )

    @patch.object(pygeocoder.Geocoder, 'geocode', side_effect=fake_geocode)
    @patch('elections.st_paul_municipal_2015.views.frontpage.requests')
    def test_front_page_good_address_outside(self, patched_requests, patched_geocode):
        patched_requests.get.side_effect = fake_represent_boundaries
        response = self.app.get('/')
        form = response.forms['form-address']
        form['address'] = 'Empire State Building, New York'
        response = form.submit()
        # FIXME: I'm not sure this is what's really intended, since it
        # would be better to stay on the front page with a validation
        # error saying the area is outside the twin cities, but this
        # is what the current lookup code from Datamade does:
        self.assertEqual(response.status_code, 302)
        split_location = urlsplit(response.location)
        self.assertEqual(
            split_location.path,
            '/areas/ocd-division,country:us,state:ny,place:new_york,council_district:4',
        )

    def test_area_page(self):
        response = self.app.get(
            '/areas/ocd-division,country:us,state:mn,place:st_paul,ward:3;ocd-division,country:us,state:mn,place:st_paul'
        )
        self.assertEqual(response.status_code, 200)

    def test_areas_of_type_page(self):
        response = self.app.get('/areas-of-type/WARD')
        self.assertEqual(response.status_code, 200)
        self.assertIn(
            '<a href="/areas/ocd-division,country:us,state:mn,place:st_paul,ward:3">Ward 3</a>',
            response
        )
        self.assertNotIn(
            '<a href="/areas/ocd-division,country:us,state:mn,place:st_paul">Saint Paul</a>',
            response
        )
