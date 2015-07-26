"""
Basic smoke tests for OfficialDocument model
"""

from django.test import TestCase

from official_documents.models import OfficialDocument

class TestModels(TestCase):

    def test_unicode(self):
        doc = OfficialDocument(
            post_id='XXX',
            source_url="http://example.com/",
        )

        self.assertEqual(unicode(doc), u"XXX (http://example.com/)")
