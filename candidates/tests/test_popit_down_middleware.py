from mock import patch

from django.contrib.sites.models import Site

from django_webtest import TransactionWebTest

from requests.adapters import ConnectionError
from slumber.exceptions import HttpServerError

def raise_connection_error(*args, **kwargs):
    raise ConnectionError()

def raise_http_server_error(*args, **kwargs):
    raise HttpServerError('Server Error 503: blah blah')

class TestPopItDown(TransactionWebTest):

    def setUp(self):
        self.site = Site.objects.create(domain='example.com', name='YNR')

    @patch('candidates.popit.PopIt')
    def test_constituencies_page_popit_connection_error(self, mock_popit):
        with self.settings(SITE_ID=self.site.id):
            mock_popit.side_effect = raise_connection_error
            response = self.app.get('/election/2015/constituencies', expect_errors=True)
            self.assertEqual(response.status_code, 503)
            self.assertIn('YNR is temporarily unavailable', unicode(response))

    @patch('candidates.popit.PopIt')
    def test_constituencies_page_popit_http_server_error(self, mock_popit):
        with self.settings(SITE_ID=self.site.id):
            mock_popit.side_effect = raise_http_server_error
            response = self.app.get('/election/2015/constituencies', expect_errors=True)
            self.assertEqual(response.status_code, 503)
            self.assertIn('YNR is temporarily unavailable', unicode(response))
