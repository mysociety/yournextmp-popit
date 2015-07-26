from django.test import TestCase

from ..popit import merge_popit_people

class TestMergePeople(TestCase):

    def test_merge_basic_unknown_details(self):
        primary = {
            'foo': 'bar',
            'quux': 'xyzzy',
        }
        secondary = {
            'foo': 'baz',
            'hello': 'goodbye',
        }
        merged = merge_popit_people(primary, secondary)
        self.assertEqual(
            merged,
            {
                'foo': 'bar',
                'quux': 'xyzzy',
                'hello': 'goodbye',
            }
        )

    def test_merge_arrays(self):
        primary = {
            'some-list': ['a', 'b', 'c'],
        }
        secondary = {
            'some-list': ['b', 'c', 'd'],
        }
        merged = merge_popit_people(primary, secondary)
        self.assertEqual(
            merged,
            {
                'some-list': ['a', 'b', 'c', 'd'],
            }
        )

    def test_merge_array_primary_null(self):
        primary = {
            'some-list': None,
        }
        secondary = {
            'some-list': ['a', 'b', 'c'],
        }
        merged = merge_popit_people(primary, secondary)
        self.assertEqual(
            merged,
            {
                'some-list': ['a', 'b', 'c'],
            }
        )

    def test_merge_array_primary_null(self):
        primary = {
            'some-list': None,
        }
        secondary = {
            'some-list': ['a', 'b', 'c'],
        }
        merged = merge_popit_people(primary, secondary)
        self.assertEqual(
            merged,
            {
                'some-list': ['a', 'b', 'c'],
            }
        )

    def test_merge_array_secondary_null(self):
        primary = {
            'some-list': ['a', 'b', 'c'],
        }
        secondary = {
            'some-list': None,
        }
        merged = merge_popit_people(primary, secondary)
        self.assertEqual(
            merged,
            {
                'some-list': ['a', 'b', 'c'],
            }
        )

    def test_merge_standing_in_contradicting(self):
        primary = {
            'standing_in': {
                '2010': {
                    'name': 'Edinburgh East',
                    'post_id': '14419',
                    'mapit_url': 'http://mapit.mysociety.org/area/14419',
                },
                '2015': {
                    'name': 'Edinburgh North and Leith',
                    'post_id': '14420',
                    'mapit_url': 'http://mapit.mysociety.org/area/14420',
                    'elected': True,
                },
            }
        }
        secondary = {
            'standing_in': {
                '2010': {
                    'name': 'Aberdeen South',
                    'post_id': '14399',
                    'mapit_url': 'http://mapit.mysociety.org/area/14399',
                },
                '2015': {
                    'name': 'Aberdeen North',
                    'post_id': '14398',
                    'mapit_url': 'http://mapit.mysociety.org/area/14398',
                },
            },
        }
        merged = merge_popit_people(primary, secondary)
        self.assertEqual(
            merged,
            {
                'standing_in': {
                    '2010': {
                        'name': 'Edinburgh East',
                        'post_id': '14419',
                    'mapit_url': 'http://mapit.mysociety.org/area/14419',
                    },
                    '2015': {
                        'name': 'Edinburgh North and Leith',
                        'post_id': '14420',
                        'mapit_url': 'http://mapit.mysociety.org/area/14420',
                        'elected': True,
                    },
                }
            }
        )

    def test_merge_standing_in_2015_null_in_primary(self):
        primary = {
            'standing_in': {
                '2010': {
                    'name': 'Edinburgh East',
                    'post_id': '14419',
                    'mapit_url': 'http://mapit.mysociety.org/area/14419',
                },
                '2015': None,
            }
        }
        secondary = {
            'standing_in': {
                '2010': {
                    'name': 'Aberdeen South',
                    'post_id': '14399',
                    'mapit_url': 'http://mapit.mysociety.org/area/14399',
                },
                '2015': {
                    'name': 'Aberdeen North',
                    'post_id': '14398',
                    'mapit_url': 'http://mapit.mysociety.org/area/14398',
                    'elected': False,
                },
            },
        }
        merged = merge_popit_people(primary, secondary)
        self.assertEqual(
            merged,
            {
                'standing_in': {
                    '2010': {
                        'name': 'Edinburgh East',
                        'post_id': '14419',
                        'mapit_url': 'http://mapit.mysociety.org/area/14419',
                    },
                    '2015': {
                        'name': 'Aberdeen North',
                        'post_id': '14398',
                        'mapit_url': 'http://mapit.mysociety.org/area/14398',
                        'elected': False,
                    },
                }
            }
        )

    def test_merge_standing_in_2015_null_in_secondary(self):
        primary = {
            'standing_in': {
                '2010': {
                    'name': 'Edinburgh East',
                    'post_id': '14419',
                    'mapit_url': 'http://mapit.mysociety.org/area/14419',
                },
                '2015': {
                    'name': 'Edinburgh North and Leith',
                    'post_id': '14420',
                    'mapit_url': 'http://mapit.mysociety.org/area/14420',
                },
            }
        }
        secondary = {
            'standing_in': {
                '2010': {
                    'name': 'Aberdeen South',
                    'post_id': '14399',
                    'mapit_url': 'http://mapit.mysociety.org/area/14399',
                },
                '2015': None
            },
        }
        merged = merge_popit_people(primary, secondary)
        self.assertEqual(
            merged,
            {
                'standing_in': {
                    '2010': {
                        'name': 'Edinburgh East',
                        'post_id': '14419',
                        'mapit_url': 'http://mapit.mysociety.org/area/14419',
                    },
                    '2015': {
                        'name': 'Edinburgh North and Leith',
                        'post_id': '14420',
                        'mapit_url': 'http://mapit.mysociety.org/area/14420',
                    },
                }
            }
        )

    def test_merge_conflicting_names(self):
        primary = {
            'name': 'Dave Cameron',
        }
        secondary = {
            'name': 'David Cameron',
        }
        merged = merge_popit_people(primary, secondary)
        self.assertEqual(
            merged,
            {
                'name': 'Dave Cameron',
                'other_names': [
                    {'name': 'David Cameron'}
                ]
            }
        )

    def test_fuller_merge_example(self):
        primary = {
            "name": "Julian Huppert",
            "other_names": [
                {
                    "end_date": None,
                    "id": "54b3fadc1f10dde30b97b3c4",
                    "name": "Julian Leon Huppert",
                    "note": "His full name, including the middle name ",
                    "start_date": None
                }
            ],
            "party_ppc_page_url": "http://www.libdems.org.uk/julian_huppert",
            "proxy_image": "http://candidates-posts.127.0.0.1.xip.io:3000/image-proxy//http%3A%2F%2Fyournextmp.popit.mysociety.org%2Fpersons%2F47%2Fimage%2F5481e8e0b150e238702c060d",
            "twitter_username": "JulianHuppert",
            "wikipedia_url": "https://en.wikipedia.org/wiki/Julian_Huppert"
        }
        secondary = {
            "name": "Julian Huppert As Well",
            "other_names": [],
            "party_ppc_page_url": "",
            "proxy_image": None,
            "twitter_username": "",
            "wikipedia_url": ""
        }
        expected_result = {
            "name": "Julian Huppert",
            "other_names": [
                {
                    "end_date": None,
                    "id": "54b3fadc1f10dde30b97b3c4",
                    "name": "Julian Leon Huppert",
                    "note": "His full name, including the middle name ",
                    "start_date": None
                },
                {
                    'name': 'Julian Huppert As Well',
                },
            ],
            "party_ppc_page_url": "http://www.libdems.org.uk/julian_huppert",
            "proxy_image": "http://candidates-posts.127.0.0.1.xip.io:3000/image-proxy//http%3A%2F%2Fyournextmp.popit.mysociety.org%2Fpersons%2F47%2Fimage%2F5481e8e0b150e238702c060d",
            "twitter_username": "JulianHuppert",
            "wikipedia_url": "https://en.wikipedia.org/wiki/Julian_Huppert"
        }
        merged = merge_popit_people(primary, secondary)
        self.assertEqual(
            merged,
            expected_result
        )

    def test_merge_conflicting_names_previous_other_names(self):
        primary = {
            'name': 'Dave Cameron',
            'other_names': [
                {'name': 'David W D Cameron'}
            ]
        }
        secondary = {
            'name': 'David Cameron',
            'other_names': [
                {'name': 'David William Donald Cameron'}
            ]
        }
        merged = merge_popit_people(primary, secondary)
        self.assertEqual(
            set(merged.keys()),
            set(['name', 'other_names'])
        )
        self.assertEqual(merged['name'], 'Dave Cameron')
        sorted_other_names = sorted(
            merged['other_names'],
            key=lambda e: e['name']
        )
        self.assertEqual(
            sorted_other_names,
            [
                {'name': 'David Cameron'},
                {'name': 'David W D Cameron'},
                {'name': 'David William Donald Cameron'},
            ],
        )

    def test_merge_versions(self):
        primary = {
            'name': 'Dave Cameron',
            'versions': [
                {
                    "version_id": "12fdb2d20e9e0753",
                    "information_source": "Some random update",
                },
                {
                    "version_id": "3570e9e02d2bdf21",
                    "information_source": "Original import",
                },
            ]
        }
        secondary = {
            'name': 'David Cameron',
            'versions': [
                {
                    "version_id": "b6fafb50a424b012",
                    "information_source": "Creation of a duplicate",
                },
            ]
        }
        merged = merge_popit_people(primary, secondary)
        self.assertEqual(
            merged,
            {
                'name': 'Dave Cameron',
                'other_names': [
                    {'name': 'David Cameron'}
                ],
                'versions': [
                    {
                        "version_id": "12fdb2d20e9e0753",
                        "information_source": "Some random update",
                    },
                    {
                        "version_id": "3570e9e02d2bdf21",
                        "information_source": "Original import",
                    },
                    {
                        "version_id": "b6fafb50a424b012",
                        "information_source": "Creation of a duplicate",
                    },
                ]
            }
        )
