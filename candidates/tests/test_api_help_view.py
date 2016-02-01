# -*- coding: utf-8 -*-

from __future__ import unicode_literals

from django_webtest import WebTest

from . import factories

class TestApiHelpView(WebTest):

    def setUp(self):
        wmc_area_type = factories.AreaTypeFactory.create()
        commons = factories.ParliamentaryChamberFactory.create()
        factories.ElectionFactory.create(
            slug='2015',
            name='2015 General Election',
            area_types=(wmc_area_type,),
            organization=commons
        )


    def test_api_help(self):
        response = self.app.get('/help/api')
        self.assertEqual(response.status_code, 200)

        self.assertIn(
            'Download of the 2015 General Election candidates',
            response)

        self.assertIn(
            "The browsable base URL of the site's read-only API is: <a href=\"http://localhost:80/api/v0.9/\">http://localhost:80/api/v0.9/</a>",
            response
        )
