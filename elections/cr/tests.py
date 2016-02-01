# -*- coding: utf-8 -*-

from __future__ import unicode_literals

from django_webtest import WebTest
from nose.plugins.attrib import attr

@attr(country='cr')
class CostaRicaTests(WebTest):

    def test_front_page(self):
        # Just a smoke test, e.g. to check that all the assets
        # required are present...
        response = self.app.get('/')
        self.assertEqual(response.status_code, 200)
