# Smoke tests for viewing a candidate's page

from __future__ import unicode_literals

from datetime import date, timedelta
import re

from django.conf import settings
from django.test.utils import override_settings
from django_webtest import WebTest

from .factories import (
    AreaTypeFactory, ElectionFactory, CandidacyExtraFactory,
    ParliamentaryChamberFactory, PartyFactory, PartyExtraFactory,
    PersonExtraFactory, PostExtraFactory
)

election_date_before = lambda r: {'DATE_TODAY': date.today()}
election_date_after = lambda r: {'DATE_TODAY': date.today() + timedelta(days=28)}
processors = settings.TEMPLATE_CONTEXT_PROCESSORS
processors_before = processors + ("candidates.tests.test_person_view.election_date_before",)
processors_after = processors + ("candidates.tests.test_person_view.election_date_after",)


class TestPersonView(WebTest):

    def setUp(self):
        wmc_area_type = AreaTypeFactory.create()
        election = ElectionFactory.create(
            slug='2015',
            name='2015 General Election',
            area_types=(wmc_area_type,)
        )
        commons = ParliamentaryChamberFactory.create()
        post_extra = PostExtraFactory.create(
            elections=(election,),
            base__organization=commons,
            slug='65808',
            base__label='Member of Parliament for Dulwich and West Norwood'
        )
        person_extra = PersonExtraFactory.create(
            base__id='2009',
            base__name='Tessa Jowell'
        )
        PartyFactory.reset_sequence()
        party_extra = PartyExtraFactory.create()
        CandidacyExtraFactory.create(
            election=election,
            base__person=person_extra.base,
            base__post=post_extra.base,
            base__on_behalf_of=party_extra.base
        )

    def test_get_tessa_jowell(self):
        response = self.app.get('/person/2009/tessa-jowell')
        self.assertTrue(
            re.search(
                r'''(?msx)
  <h1>Tessa\s+Jowell</h1>\s*
  <p>Candidate\s+for\s+
  <a\s+href="/election/2015/post/65808/dulwich-and-west-norwood">Dulwich\s+
  and\s+West\s+Norwood</a>\s+in\ 2015\s+General\s+Election\s*</p>''',
                response.text
            )
        )

    @override_settings(TEMPLATE_CONTEXT_PROCESSORS=processors_before)
    def test_get_tessa_jowell_before_election(self):
        response = self.app.get('/person/2009/tessa-jowell')
        self.assertContains(response, 'Contesting in the 2015 General Election')

    @override_settings(TEMPLATE_CONTEXT_PROCESSORS=processors_after)
    def test_get_tessa_jowell_after_election(self):
        response = self.app.get('/person/2009/tessa-jowell')
        self.assertContains(response, 'Contested in the 2015 General Election')

    def test_get_non_existent(self):
        response = self.app.get(
            '/person/987654/imaginary-person',
            expect_errors=True
        )
        self.assertEqual(response.status_code, 404)
