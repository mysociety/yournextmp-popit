from __future__ import unicode_literals

import json

from django.utils.six.moves.urllib_parse import urlsplit

from django_webtest import WebTest

from .auth import TestUserMixin

from .factories import (
    AreaTypeFactory, ElectionFactory, ParliamentaryChamberFactory,
    PartyFactory, PartyExtraFactory, PostExtraFactory, PartySetFactory
)


class TestCopyrightAssignment(TestUserMixin, WebTest):

    def setUp(self):
        wmc_area_type = AreaTypeFactory.create()
        gb_parties = PartySetFactory.create(slug='gb', name='Great Britain')
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
            base__label='Member of Parliament for Dulwich and West Norwood',
            party_set=gb_parties,
        )
        PartyExtraFactory.reset_sequence()
        PartyFactory.reset_sequence()
        self.parties = {}
        for i in range(0, 4):
            party_extra = PartyExtraFactory.create()
            gb_parties.parties.add(party_extra.base)
            self.parties[party_extra.slug] = party_extra

    def test_new_person_submission_refused_copyright(self):
        response = self.app.get(
            '/constituency/65808/dulwich-and-west-norwood',
            user=self.user_refused,
        )
        split_location = urlsplit(response.location)
        self.assertEqual(
            '/copyright-question',
            split_location.path
        )
        self.assertEqual(
            'next=/constituency/65808/dulwich-and-west-norwood',
            split_location.query
        )

    def test_copyright_assigned(self):
        response = self.app.get(
            '/constituency/65808/dulwich-and-west-norwood',
            user=self.user_refused,
            auto_follow=True
        )

        form = response.forms['copyright_assignment']
        form['assigned_to_dc'] = True
        form_response = form.submit()

        split_location = urlsplit(form_response.location)
        self.assertEqual(
            '/constituency/65808/dulwich-and-west-norwood',
            split_location.path
        )

        agreement = self.user_refused.terms_agreement
        agreement.refresh_from_db()
        self.assertTrue(agreement.assigned_to_dc)

    def test_copyright_assignment_refused(self):
        response = self.app.get(
            '/constituency/65808/dulwich-and-west-norwood',
            user=self.user_refused,
            auto_follow=True
        )

        response.mustcontain(no='You can only edit data on example.com')

        form = response.forms['copyright_assignment']
        form['assigned_to_dc'] = False
        form_response = form.submit()

        form_response.mustcontain('You can only edit data on example.com')

        agreement = self.user_refused.terms_agreement
        agreement.refresh_from_db()
        self.assertFalse(agreement.assigned_to_dc)
