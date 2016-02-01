from __future__ import unicode_literals

import re

from django_webtest import WebTest

from .factories import (
    AreaTypeFactory, ElectionFactory,
    PostExtraFactory, ParliamentaryChamberFactory,
)

class TestConstituencyDetailView(WebTest):

    def setUp(self):
        wmc_area_type = AreaTypeFactory.create()
        commons = ParliamentaryChamberFactory.create()
        election = ElectionFactory.create(
            slug='2015',
            name='2015 General Election',
            area_types=(wmc_area_type,),
            organization=commons
        )
        PostExtraFactory.create(
            elections=(election,),
            base__organization=commons,
            slug='65808',
            base__label='Member of Parliament for Dulwich and West Norwood'
        )

    def test_constituencies_page(self):
        # Just a smoke test to check that the page loads:
        response = self.app.get('/election/2015/constituencies')
        dulwich= response.html.find(
            'a', text=re.compile(r'Dulwich and West Norwood')
        )
        self.assertTrue(dulwich)
