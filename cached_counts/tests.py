# -*- coding: utf-8 -*-

from __future__ import unicode_literals

import json

from django_webtest import WebTest

from popolo.models import Person

from candidates.tests import factories


class CachedCountTestCase(WebTest):
    def setUp(self):
        commons = factories.ParliamentaryChamberFactory.create()
        election = factories.ElectionFactory.create()
        earlier_election = factories.EarlierElectionFactory.create()
        factories.PostFactory.reset_sequence()
        factories.PostExtraFactory.reset_sequence()
        posts_extra = [
            factories.PostExtraFactory.create(
                elections=(election, earlier_election),
                base__organization=commons
            )
            for i in range(4)
        ]
        factories.PartyFactory.reset_sequence()
        factories.PartyExtraFactory.reset_sequence()
        parties_extra = [
            factories.PartyExtraFactory.create()
            for i in range(7)
        ]
        i = 0
        candidacy_counts = {
            '14419': 10,
            '14420': 3,
            '65808': 5,
            '65913': 0,
        }
        for post_extra in posts_extra:
            candidacy_count = candidacy_counts[post_extra.slug]
            for n in range(candidacy_count):
                person_extra = factories.PersonExtraFactory.create(
                    base__id=str(7000 + i),
                    base__name='Test Candidate {0}'.format(i)
                )
                party = parties_extra[n%5]
                factories.CandidacyExtraFactory.create(
                    election=election,
                    base__person=person_extra.base,
                    base__post=post_extra.base,
                    base__on_behalf_of=party.base,
                )
                i += 1
        # Now create a couple of candidacies in the earlier election.
        # First, one sticking with the same party (but in a different
        # post):
        factories.CandidacyExtraFactory.create(
            election=earlier_election,
            base__person=Person.objects.get(id=7000),
            base__post=posts_extra[1].base,
            base__on_behalf_of=parties_extra[0].base,
        )
        # Now one in the same post but standing for a different party:
        factories.CandidacyExtraFactory.create(
            election=earlier_election,
            base__person=Person.objects.get(id=7001),
            base__post=posts_extra[1].base,
            base__on_behalf_of=parties_extra[2].base,
        )

    def test_reports_top_page(self):
        response = self.app.get('/numbers/')
        self.assertEqual(response.status_code, 200)
        current_div = response.html.find(
            'div', {'id': 'statistics-election-general-election'}
        )
        self.assertTrue(current_div)
        self.assertIn('Total candidates: 18', str(current_div))
        earlier_div = response.html.find(
            'div', {'id': 'statistics-election-earlier-general-election'}
        )
        self.assertIn('Total candidates: 2', str(earlier_div))

    def test_reports_top_page_json(self):
        response = self.app.get('/numbers/?format=json')
        data = json.loads(response.body.decode())
        self.assertEqual(
            data,
            {
                'current': [
                    {
                        'total': 18,
                        'id': "general-election",
                        'name': "General Election",
                        'prior_elections': [
                            {
                                "percentage": 900.0,
                                "name": 'Earlier General Election',
                                "new_candidates": 16,
                                "standing_again": 2,
                                "standing_again_different_party": 1,
                                "standing_again_same_party": 1
                            },
                        ]
                    }
                ],
                'past': [
                    {
                        'total': 2,
                        'id': "earlier-general-election",
                        'name': "Earlier General Election"
                    }
                ]
            }
        )

    def test_attention_needed_page(self):
        response = self.app.get('/numbers/attention-needed')
        rows = [
            tuple(td.decode() for td in row.find_all('td'))
            for row in response.html.find_all('tr')
        ]
        self.assertEqual(
            rows,
            [
                ('<td>Earlier General Election</td>',
                 '<td><a href="/election/earlier-general-election/post/65913/camberwell-and-peckham">Member of Parliament for Camberwell and Peckham</a></td>',
                 '<td>0</td>'),
                ('<td>Earlier General Election</td>',
                 '<td><a href="/election/earlier-general-election/post/65808/dulwich-and-west-norwood">Member of Parliament for Dulwich and West Norwood</a></td>',
                 '<td>0</td>'),
                ('<td>Earlier General Election</td>',
                 '<td><a href="/election/earlier-general-election/post/14419/edinburgh-east">Member of Parliament for Edinburgh East</a></td>',
                 '<td>0</td>'),
                ('<td>General Election</td>',
                 '<td><a href="/election/general-election/post/65913/camberwell-and-peckham">Member of Parliament for Camberwell and Peckham</a></td>',
                 '<td>0</td>'),
                ('<td>Earlier General Election</td>',
                 '<td><a href="/election/earlier-general-election/post/14420/edinburgh-north-and-leith">Member of Parliament for Edinburgh North and Leith</a></td>',
                 '<td>2</td>'),
                ('<td>General Election</td>',
                 '<td><a href="/election/general-election/post/14420/edinburgh-north-and-leith">Member of Parliament for Edinburgh North and Leith</a></td>',
                 '<td>3</td>'),
                ('<td>General Election</td>',
                 '<td><a href="/election/general-election/post/65808/dulwich-and-west-norwood">Member of Parliament for Dulwich and West Norwood</a></td>',
                 '<td>5</td>'),
                ('<td>General Election</td>',
                 '<td><a href="/election/general-election/post/14419/edinburgh-east">Member of Parliament for Edinburgh East</a></td>',
                 '<td>10</td>')
            ]
        )

    def test_post_counts_page(self):
        response = self.app.get('/numbers/election/general-election/posts')
        self.assertEqual(response.status_code, 200)
        rows = [
            tuple(td.decode() for td in row.find_all('td'))
            for row in response.html.find_all('tr')
        ]
        self.assertEqual(
            rows,
            [
                ('<td><a href="/election/general-election/post/14419/edinburgh-east">Member of Parliament for Edinburgh East</a></td>',
                 '<td>10</td>'),
                ('<td><a href="/election/general-election/post/65808/dulwich-and-west-norwood">Member of Parliament for Dulwich and West Norwood</a></td>',
                 '<td>5</td>'),
                ('<td><a href="/election/general-election/post/14420/edinburgh-north-and-leith">Member of Parliament for Edinburgh North and Leith</a></td>',
                 '<td>3</td>'),
                ('<td><a href="/election/general-election/post/65913/camberwell-and-peckham">Member of Parliament for Camberwell and Peckham</a></td>',
                 '<td>0</td>'),
            ]
        )

    def test_party_counts_page(self):
        response = self.app.get('/numbers/election/general-election/parties')
        self.assertEqual(response.status_code, 200)
        rows = [
            tuple(td.decode() for td in row.find_all('td'))
            for row in response.html.find_all('tr')
        ]
        self.assertEqual(
            rows,
            [
                ('<td><a href="/election/general-election/party/party:63/green-party">Green Party</a></td>',
                 '<td>4</td>'),
                ('<td><a href="/election/general-election/party/party:53/labour-party">Labour Party</a></td>',
                 '<td>4</td>'),
                ('<td><a href="/election/general-election/party/party:90/liberal-democrats">Liberal Democrats</a></td>',
                 '<td>4</td>'),
                ('<td><a href="/election/general-election/party/party:52/conservative-party">Conservative Party</a></td>',
                 '<td>3</td>'),
                ('<td><a href="/election/general-election/party/party:10004/party-4">Party 4</a></td>',
                 '<td>3</td>'),
                ('<td>Party 5</td>',
                 '<td>0</td>'),
                ('<td>Party 6</td>',
                 '<td>0</td>')
            ]
        )
