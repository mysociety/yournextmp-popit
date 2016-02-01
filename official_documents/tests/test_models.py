"""
Basic smoke tests for OfficialDocument model
"""

from __future__ import unicode_literals

from django.test import TestCase

from official_documents.models import OfficialDocument

from candidates.tests.factories import (
    AreaTypeFactory, ElectionFactory, ParliamentaryChamberFactory,
    PostExtraFactory
)

from compat import text_type


class TestModels(TestCase):

    def setUp(self):
        wmc_area_type = AreaTypeFactory.create()
        election = ElectionFactory.create(
            slug='2015',
            name='2015 General Election',
            area_types=(wmc_area_type,)
        )
        commons = ParliamentaryChamberFactory.create()
        self.post = PostExtraFactory.create(
            elections=(election,),
            base__organization=commons,
            slug='65808',
            base__label='Member of Parliament for Dulwich and West Norwood'
        )

    def test_unicode(self):
        doc = OfficialDocument(
            post=self.post.base,
            source_url="http://example.com/",
        )

        self.assertEqual(text_type(doc), "65808 (http://example.com/)")
