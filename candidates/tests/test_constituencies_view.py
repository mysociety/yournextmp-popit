import re

from mock import patch

from django_webtest import WebTest

class TestConstituencyDetailView(WebTest):

    @patch('candidates.popit.PopIt')
    def test_constituencies_page(self, mock_popit):
        # Just a smoke test to check that the page loads:
        response = self.app.get('/election/2015/constituencies')
        aberdeen_north = response.html.find(
            'a', text=re.compile(r'York Outer')
        )
        self.assertTrue(aberdeen_north)
