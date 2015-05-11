# Smoke tests for viewing a candidate's page

from datetime import date
import re

from mock import patch

from django.conf import settings
from django.test.utils import override_settings
from django_webtest import WebTest

from .fake_popit import FakePersonCollection
from candidates.models import election_date_2015


election_date_before = lambda r: {'DATE_ELECTION': election_date_2015, 'DATE_TODAY': date(2015, 5, 1)}
election_date_after = lambda r: {'DATE_ELECTION': election_date_2015, 'DATE_TODAY': date(2015, 6, 1)}
processors = settings.TEMPLATE_CONTEXT_PROCESSORS
processors_before = processors + ("candidates.tests.test_person_view.election_date_before",)
processors_after = processors + ("candidates.tests.test_person_view.election_date_after",)


@patch('candidates.popit.PopIt')
class TestPersonView(WebTest):

    def test_get_tessa_jowell(self, mock_popit):
        mock_popit.return_value.persons = FakePersonCollection
        response = self.app.get('/person/2009/tessa-jowell')
        self.assertTrue(
            re.search(
                r'''(?msx)
  <h1>Tessa\s+Jowell</h1>\s*
  <p>Candidate\s+for\s+
  <a\s+href="/constituency/65808/dulwich-and-west-norwood">Dulwich\s+
  and\s+West\s+Norwood</a>\s+in\ 2015\s*</p>''',
                unicode(response)
            )
        )

    @override_settings(TEMPLATE_CONTEXT_PROCESSORS=processors_before)
    def test_get_tessa_jowell_before_election(self, mock_popit):
        mock_popit.return_value.persons = FakePersonCollection
        response = self.app.get('/person/2009/tessa-jowell')
        self.assertContains(response, 'Contesting in 2015')

    @override_settings(TEMPLATE_CONTEXT_PROCESSORS=processors_after)
    def test_get_tessa_jowell_after_election(self, mock_popit):
        mock_popit.return_value.persons = FakePersonCollection
        response = self.app.get('/person/2009/tessa-jowell')
        self.assertContains(response, 'Contested in 2015')

    def test_get_non_existent(self, mock_popit):
        mock_popit.return_value.persons = FakePersonCollection
        response = self.app.get(
            '/person/987654/imaginary-person',
            expect_errors=True
        )
        self.assertEqual(response.status_code, 404)
