from django.test import TestCase

from candidates.diffs import get_version_diffs

class TestVersionDiffs(TestCase):

    def test_get_version_diffs(self):
        versions = [
            {
                'user': 'john',
                'information_source': 'Manual correction by a user',
                'data': {
                    'a': 'alpha',
                    'b': 'beta',
                    'g': '',
                    'h': None,
                    'l': 'lambda',
                }
            },
            {
                'information_source': 'Updated by a script',
                'data': {
                    'a': 'alpha',
                    'b': 'LATIN SMALL LETTER B',
                    'd': 'delta',
                    'g': None,
                    'h': '',
                    'l': 'lambda',
                }
            },
            {
                'information_source': 'Original imported data',
                'data': {
                    'a': 'alpha',
                    'b': 'beta',
                    'l': None,
                }
            },
        ]

        expected_result = [
            {
                'user': 'john',
                'information_source': 'Manual correction by a user',
                'data': {
                    'a': 'alpha',
                    'b': 'beta',
                    'g': '',
                    'h': None,
                    'l': 'lambda',
                },
                'diff': [
                    {
                        'op': u'remove',
                        'path': 'd',
                        'previous_value': 'delta',
                    },
                    {
                        'op': u'replace',
                        'path': 'b',
                        'previous_value': 'LATIN SMALL LETTER B',
                        'value': 'beta',
                    }
                ]
            },
            {
                'information_source': 'Updated by a script',
                'data': {
                    'a': 'alpha',
                    'b': 'LATIN SMALL LETTER B',
                    'd': 'delta',
                    'g': None,
                    'h': '',
                    'l': 'lambda',
                },
                'diff': [
                    {
                        'op': 'add',
                        'path': 'd',
                        'value': 'delta',
                    },
                    {
                        'op': 'add',
                        'path': 'l',
                        'previous_value': None,
                        'value': 'lambda',
                    },
                    {
                        'op': 'replace',
                        'path': 'b',
                        'previous_value': 'beta',
                        'value': 'LATIN SMALL LETTER B',
                    },
                ]
            },
            {
                'information_source': 'Original imported data',
                'data': {
                    'a': 'alpha',
                    'b': 'beta',
                    'l': None,
                },
                'diff': [
                    {
                        'op': 'add',
                        'path': 'a',
                        'value': 'alpha',
                    },
                    {
                        'op': 'add',
                        'path': 'b',
                        'value': 'beta',
                    },
                ]
            },
        ]

        versions_with_diffs = get_version_diffs(versions)

        self.assertEqual(expected_result, versions_with_diffs)

    def test_versions_2010_then_adding_2015(self):
        versions = [
            {
                'information_source': 'After clicking "Standing again"',
                'data': {
                    'standing_in': {
                        '2010': {
                            'name': 'South Cambridgeshire',
                            'post_id': '65922',
                            'mapit_url': 'http://mapit.mysociety.org/area/65922',
                        },
                        '2015': {
                            'name': 'Edinburgh North and Leith',
                            'post_id': '14420',
                            'mapit_url': 'http://mapit.mysociety.org/area/14420',
                        },
                    }
                }
            },
            {
                'information_source': 'Original imported data',
                'data': {
                    'standing_in': {
                        '2010': {
                            'name': 'South Cambridgeshire',
                            'post_id': '65922',
                            'mapit_url': 'http://mapit.mysociety.org/area/65922',
                        },
                    }
                }
            },
        ]

        expected_result = [
            {
                'information_source': 'After clicking "Standing again"',
                'data': {
                    'standing_in': {
                        '2010': {
                            'name': 'South Cambridgeshire',
                            'post_id': '65922',
                            'mapit_url': 'http://mapit.mysociety.org/area/65922',
                        },
                        '2015': {
                            'name': 'Edinburgh North and Leith',
                            'post_id': '14420',
                            'mapit_url': 'http://mapit.mysociety.org/area/14420',
                        },
                    }
                },
                'diff': [
                    {
                        'op': 'add',
                        'path': 'standing_in/2015',
                        'value': 'is known to be standing in Edinburgh North and Leith in the 2015 General Election',
                    }
                ]
            },
            {
                'information_source': 'Original imported data',
                'data': {
                    'standing_in': {
                        '2010': {
                            'name': 'South Cambridgeshire',
                            'post_id': '65922',
                            'mapit_url': 'http://mapit.mysociety.org/area/65922',
                        },
                    }
                },
                'diff':[
                    {
                        'op': 'add',
                        'path': 'standing_in',
                        'value': 'was known to be standing in South Cambridgeshire in the 2010 General Election',
                    }
                ]
            },
        ]

        versions_with_diffs = get_version_diffs(versions)

        self.assertEqual(expected_result, versions_with_diffs)

    def test_versions_2010_then_definitely_not_2015(self):
        versions = [
            {
                'information_source': 'After clicking "Not standing again"',
                'data': {
                    'standing_in': {
                        '2010': {
                            'name': 'South Cambridgeshire',
                            'post_id': '65922',
                            'mapit_url': 'http://mapit.mysociety.org/area/65922',
                        },
                        '2015': None,
                    }
                }
            },
            {
                'information_source': 'Original imported data',
                'data': {
                    'standing_in': {
                        '2010': {
                            'name': 'South Cambridgeshire',
                            'post_id': '65922',
                            'mapit_url': 'http://mapit.mysociety.org/area/65922',
                        },
                    }
                }
            },
        ]

        expected_result = [
            {
                'information_source': 'After clicking "Not standing again"',
                'data': {
                    'standing_in': {
                        '2010': {
                            'name': 'South Cambridgeshire',
                            'post_id': '65922',
                            'mapit_url': 'http://mapit.mysociety.org/area/65922',
                        },
                        '2015': None,
                    }
                },
                'diff': [
                    {
                        'op': 'add',
                        'path': 'standing_in/2015',
                        'value': 'is known not to be standing in the 2015 General Election',
                    }
                ]
            },
            {
                'information_source': 'Original imported data',
                'data': {
                    'standing_in': {
                        '2010': {
                            'name': 'South Cambridgeshire',
                            'post_id': '65922',
                            'mapit_url': 'http://mapit.mysociety.org/area/65922',
                        },
                    }
                },
                'diff':[
                    {
                        'op': 'add',
                        'path': 'standing_in',
                        'value': 'was known to be standing in South Cambridgeshire in the 2010 General Election',
                    }
                ]
            },
        ]

        versions_with_diffs = get_version_diffs(versions)

        self.assertEqual(expected_result, versions_with_diffs)

    def test_versions_just_party_changed(self):
        versions = [
            {
                'information_source': 'After clicking "Not standing again"',
                'data': {
                    'party_memberships': {
                        '2010': {
                            'id': 'party:58',
                            'name': 'Mebyon Kernow - The Party for Cornwall'
                        },
                        '2015': {
                            'id': 'ynmp-party:2',
                            'name': 'Independent'
                        }
                    },
                }
            },
            {
                'information_source': 'Original imported data',
                'data': {
                    'party_memberships': {
                        '2010': {
                            'id': 'party:58',
                            'name': 'Mebyon Kernow - The Party for Cornwall'
                        },
                        '2015': {
                            'id': 'party:58',
                            'name': 'Mebyon Kernow - The Party for Cornwall'
                        }
                    },
                }
            },
        ]

        expected_result = [
            {
                'information_source': 'After clicking "Not standing again"',
                'data': {
                    'party_memberships': {
                        '2010': {
                            'id': 'party:58',
                            'name': 'Mebyon Kernow - The Party for Cornwall'
                        },
                        '2015': {
                            'id': 'ynmp-party:2',
                            'name': 'Independent'
                        }
                    },
                },
                'diff': [
                    {
                        'op': 'replace',
                        'path': 'party_memberships/2015/id',
                        'previous_value': 'is known to be standing for the party with ID party:58 in the 2015 General Election',
                        'value': 'is known to be standing for the party with ID ynmp-party:2 in the 2015 General Election',
                    },
                    {
                        'op': 'replace',
                        'path': 'party_memberships/2015/name',
                        'previous_value': 'is known to be standing for the party \'Mebyon Kernow - The Party for Cornwall\' in the 2015 General Election',
                        'value': 'is known to be standing for the party \'Independent\' in the 2015 General Election',
                    },
                ]
            },
            {
                'information_source': 'Original imported data',
                'data': {
                    'party_memberships': {
                        '2010': {
                            'id': 'party:58',
                            'name': 'Mebyon Kernow - The Party for Cornwall'
                        },
                        '2015': {
                            'id': 'party:58',
                            'name': 'Mebyon Kernow - The Party for Cornwall'
                        }
                    },
                },
                'diff':[
                    {
                        'op': 'add',
                        'path': 'party_memberships',
                        'value': 'is known to be standing for the party "Mebyon Kernow - The Party for Cornwall" in the 2015 General Election and was known to be standing for the party "Mebyon Kernow - The Party for Cornwall" in the 2010 General Election',
                    }
                ]
            },
        ]

        versions_with_diffs = get_version_diffs(versions)

        self.assertEqual(expected_result, versions_with_diffs)

    def test_versions_just_constituency_changed(self):
        versions = [
            {
                'information_source': 'After clicking "Not standing again"',
                'data': {
                    'standing_in': {
                        '2015': {'mapit_url': 'http://mapit.mysociety.org/area/65659',
                                 'name': 'Truro and Falmouth',
                                 'post_id': '65659'}
                    },
                }
            },
            {
                'information_source': 'Original imported data',
                'data': {
                    "standing_in": {
                        "2015": {
                            "post_id": "65808",
                            "name": "Dulwich and West Norwood",
                            "mapit_url": "http://mapit.mysociety.org/area/65808"
                        },
                    },
                }
            },
        ]

        expected_result = [
            {
                'information_source': 'After clicking "Not standing again"',
                'data': {
                    'standing_in': {
                        '2015': {'mapit_url': 'http://mapit.mysociety.org/area/65659',
                                 'name': 'Truro and Falmouth',
                                 'post_id': '65659'}
                    },
                },
                'diff': [
                    {
                        'op': 'replace',
                        'path': 'standing_in/2015/mapit_url',
                        'previous_value': 'is known to be standing in the constituency with MapIt URL http://mapit.mysociety.org/area/65808 in the 2015 General Election',
                        'value': 'is known to be standing in the constituency with MapIt URL http://mapit.mysociety.org/area/65659 in the 2015 General Election',
                    },
                    {
                        'op': 'replace',
                        'path': 'standing_in/2015/name',
                        'previous_value': 'is known to be standing in Dulwich and West Norwood in the 2015 General Election',
                        'value': 'is known to be standing in Truro and Falmouth in the 2015 General Election',
                    },
                    {
                        'op': 'replace',
                        'path': 'standing_in/2015/post_id',
                        'previous_value': 'is known to be standing for the post with ID 65808 in the 2015 General Election',
                        'value': 'is known to be standing for the post with ID 65659 in the 2015 General Election',
                    },
                ]
            },
            {
                'information_source': 'Original imported data',
                'data': {
                    "standing_in": {
                        "2015": {
                            "post_id": "65808",
                            "name": "Dulwich and West Norwood",
                            "mapit_url": "http://mapit.mysociety.org/area/65808"
                        },
                    },
                },
                'diff':[
                    {
                        'op': 'add',
                        'path': 'standing_in',
                        'value': 'is known to be standing in Dulwich and West Norwood in the 2015 General Election',
                    }
                ]
            },
        ]

        versions_with_diffs = get_version_diffs(versions)

        self.assertEqual(expected_result, versions_with_diffs)

    def test_remove_ids_for_version_diffs(self):
        versions = [
            {
                'user': 'john',
                'information_source': 'Manual correction by a user',
                'data': {
                    'identifiers': [
                        {
                            'scheme': 'yournextmp-candidate',
                            'identifier': '2009',
                            'id': '123456',
                        },
                    ],
                    'other_names': [
                        {
                            'note': 'Full name',
                            'start_date': None,
                            'id': '567890',
                            'end_date': None,
                            'name': 'Tessa Jane Jowell'
                        }
                    ]
                }
            },
            {
                'information_source': 'Updated by a script',
                'data': {
                    'identifiers': [
                        {
                            'scheme': 'yournextmp-candidate',
                            'identifier': '2009',
                            'id': '123457',
                        }
                    ],
                    'other_names': [
                        {
                            'note': 'Full name',
                            'start_date': None,
                            'id': '567891',
                            'end_date': None,
                            'name': 'Tessa J Jowell'
                        }
                    ]
                }
            },
        ]

        expected_result = [
            {
                'user': 'john',
                'information_source': 'Manual correction by a user',
                'data': {
                    'identifiers': [
                        {
                            'scheme': 'yournextmp-candidate',
                            'identifier': '2009',
                        },
                    ],
                    'other_names': [
                        {
                            'note': 'Full name',
                            'start_date': None,
                            'end_date': None,
                            'name': 'Tessa Jane Jowell'
                        }
                    ],
                },
                'diff': [
                    {
                        "op": "replace",
                        "path": "other_names/0",
                        "previous_value": {
                            "end_date": None,
                            "name": "Tessa J Jowell",
                            "note": "Full name",
                            "start_date": None
                        },
                        "value": {
                            "end_date": None,
                            "name": "Tessa Jane Jowell",
                            "note": "Full name",
                            "start_date": None
                        }
                    }
                ],
            },
            {
                'information_source': 'Updated by a script',
                'data': {
                    'identifiers': [
                        {
                            'scheme': 'yournextmp-candidate',
                            'identifier': '2009',
                        },
                    ],
                    'other_names': [
                        {
                            'note': 'Full name',
                            'start_date': None,
                            'end_date': None,
                            'name': 'Tessa J Jowell'
                        }
                    ]
                },
                'diff': [
                    {
                        "op": "add",
                        "path": "identifiers",
                        "value": [
                            {
                                "identifier": "2009",
                                "scheme": "yournextmp-candidate"
                            }
                        ]
                    },
                    {
                        "op": "add",
                        "path": "other_names",
                        "value": [
                            {
                                "end_date": None,
                                "name": "Tessa J Jowell",
                                "note": "Full name",
                                "start_date": None
                            }
                        ]
                    }
                ],
            },
        ]

        versions_with_diffs = get_version_diffs(versions)

        self.assertEqual(expected_result, versions_with_diffs)
