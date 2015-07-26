from mock import patch

from django_webtest import WebTest

from requests.adapters import ConnectionError
from slumber.exceptions import HttpServerError

def raise_connection_error(*args, **kwargs):
    raise ConnectionError()

def raise_http_server_error(*args, **kwargs):
    raise HttpServerError('Server Error 503: blah blah')

class TestPopItDown(WebTest):

    @patch('candidates.popit.PopIt')
    def test_constituencies_page_popit_connection_error(self, mock_popit):
        mock_popit.side_effect = raise_connection_error
        response = self.app.get('/election/2015/constituencies', expect_errors=True)
        self.assertEqual(response.status_code, 503)
        self.assertIn('YourNextMP is temporarily unavailable', unicode(response))

    @patch('candidates.popit.PopIt')
    def test_constituencies_page_popit_http_server_error(self, mock_popit):
        mock_popit.side_effect = raise_http_server_error
        response = self.app.get('/election/2015/constituencies', expect_errors=True)
        self.assertEqual(response.status_code, 503)
        self.assertIn('YourNextMP is temporarily unavailable', unicode(response))
