from __future__ import unicode_literals

from django.test import TestCase

from candidates.tests.factories import (
    AreaTypeFactory, ElectionFactory, CandidacyExtraFactory,
    ParliamentaryChamberFactory, PartyFactory, PartyExtraFactory,
    PersonExtraFactory, PostExtraFactory
)


class TestFieldView(TestCase):

    def setUp(self):
        wmc_area_type = AreaTypeFactory.create()
        self.election = ElectionFactory.create(
            slug='2015',
            name='2015 General Election',
            area_types=(wmc_area_type,)
        )
        commons = ParliamentaryChamberFactory.create()
        self.post_extra = PostExtraFactory.create(
            elections=(self.election,),
            base__organization=commons,
            slug='65808',
            base__label='Member of Parliament for Dulwich and West Norwood'
        )
        PartyExtraFactory.reset_sequence()
        PartyFactory.reset_sequence()
        self.parties = {}
        for i in range(0, 4):
            party_extra = PartyExtraFactory.create()
            self.parties[party_extra.slug] = party_extra

        person_extra = PersonExtraFactory.create(
            base__id='2009',
            base__name='Tessa Jowell'
        )

        CandidacyExtraFactory.create(
            election=self.election,
            base__person=person_extra.base,
            base__post=self.post_extra.base,
            base__on_behalf_of=self.parties['party:63'].base
        )

        person_extra = PersonExtraFactory.create(
            base__id='2010',
            base__name='Andrew Smith',
            base__email='andrew@example.com',
        )

        CandidacyExtraFactory.create(
            election=self.election,
            base__person=person_extra.base,
            base__post=self.post_extra.base,
            base__on_behalf_of=self.parties['party:63'].base
        )

    def test_context_data(self):
        url = '/tasks/email/'

        response = self.client.get(url)
        self.assertEqual(response.context['field'], 'email')
        self.assertEqual(response.context['candidates_count'], 2)
        self.assertEqual(response.context['results_count'], 1)

        self.assertContains(response, 'Tessa Jowell')

    def test_template_used(self):
        response = self.client.get('/tasks/email/')
        self.assertTemplateUsed(response, 'tasks/field.html')
