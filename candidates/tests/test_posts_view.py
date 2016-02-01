from __future__ import unicode_literals

from django_webtest import WebTest

from .factories import (
    AreaTypeFactory, ElectionFactory, EarlierElectionFactory,
    PostFactory, PostExtraFactory, ParliamentaryChamberFactory
)

class TestPostsView(WebTest):

    def setUp(self):
        wmc_area_type = AreaTypeFactory.create()
        self.election = ElectionFactory.create(
            slug='2015',
            name='2015 General Election',
            area_types=(wmc_area_type,)
        )
        self.earlier_election = EarlierElectionFactory.create(
            slug='2010',
            name='2010 General Election',
            area_types=(wmc_area_type,)
        )
        commons = ParliamentaryChamberFactory.create()
        PostFactory.reset_sequence()
        for i in range(4):
            PostExtraFactory.create(
                elections=(self.election, self.earlier_election),
                base__organization=commons
            )

    def test_single_election_posts_page(self):

        response = self.app.get('/posts')

        self.assertTrue(
            response.html.find(
                'h2', text='2015 General Election'
            )
        )

        self.assertTrue(
            response.html.find(
                'a', text='Member of Parliament for Camberwell and Peckham'
            )
        )

    def test_two_elections_posts_page(self):

        self.earlier_election.current = True
        self.earlier_election.save()

        response = self.app.get('/posts')

        self.assertTrue(
            response.html.find(
                'h2', text='2010 General Election'
            )
        )

        self.assertTrue(
            response.html.find(
                'h2', text='2015 General Election'
            )
        )
