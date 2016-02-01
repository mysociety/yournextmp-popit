from __future__ import unicode_literals

import re
from django_webtest import WebTest

from candidates.models import MembershipExtra

from .auth import TestUserMixin
from .factories import (
    AreaTypeFactory, ElectionFactory, PostExtraFactory,
    ParliamentaryChamberFactory, PersonExtraFactory,
    CandidacyExtraFactory, PartyExtraFactory, PartyFactory,
    MembershipFactory, PartySetFactory, AreaExtraFactory
)


class TestRecordWinner(TestUserMixin, WebTest):

    def setUp(self):
        wmc_area_type = AreaTypeFactory.create()
        gb_parties = PartySetFactory.create(slug='gb', name='Great Britain')
        commons = ParliamentaryChamberFactory.create()
        self.election = ElectionFactory.create(
            slug='2015',
            name='2015 General Election',
            area_types=(wmc_area_type,),
            organization=commons
        )
        dulwich_area = AreaExtraFactory.create(
            base__identifier='65808',
            base__name='Dulwich and West Norwood',
            type=wmc_area_type,
        )
        dulwich_post = PostExtraFactory.create(
            elections=(self.election,),
            base__organization=commons,
            base__area=dulwich_area.base,
            slug='65808',
            base__label='Member of Parliament for Dulwich and West Norwood',
            party_set=gb_parties,
        )

        camberwell_area = AreaExtraFactory.create(
            base__identifier='65913',
            base__name='Camberwell and Peckham',
            type=wmc_area_type,
        )
        camberwell_post = PostExtraFactory.create(
            elections=(self.election,),
            base__area=camberwell_area.base,
            base__organization=commons,
            slug='65913',
            candidates_locked=True,
            base__label='Member of Parliament for Camberwell and Peckham',
            party_set=gb_parties,
        )

        PartyFactory.reset_sequence()
        party_extra = PartyExtraFactory.create()

        tessa_jowell = PersonExtraFactory.create(
            base__id='2009',
            base__name='Tessa Jowell'
        )
        CandidacyExtraFactory.create(
            election=self.election,
            base__person=tessa_jowell.base,
            base__post=dulwich_post.base,
            base__on_behalf_of=party_extra.base
            )
        MembershipFactory.create(
            person=tessa_jowell.base,
            organization=party_extra.base
        )

        winner = PersonExtraFactory.create(
            base__id='4322',
            base__name='Helen Hayes'
        )
        CandidacyExtraFactory.create(
            election=self.election,
            base__person=winner.base,
            base__post=dulwich_post.base,
            base__on_behalf_of=party_extra.base,
            elected=True
            )
        MembershipFactory.create(
            person=winner.base,
            organization=party_extra.base
        )

        james_smith = PersonExtraFactory.create(
            base__id='2010',
            base__name='James Smith'
        )
        CandidacyExtraFactory.create(
            election=self.election,
            base__person=james_smith.base,
            base__post=camberwell_post.base,
            base__on_behalf_of=party_extra.base
            )
        MembershipFactory.create(
            person=james_smith.base,
            organization=party_extra.base
        )

    def test_constituencies_declared(self):
        response = self.app.get(
            '/election/2015/constituencies/declared'
        )

        self.assertEqual(response.status_code, 200)
        response.mustcontain('Dulwich')
        response.mustcontain('Camberwell')

        response.mustcontain('1 still undeclared (50% done)')

    def test_constituencies_declared_bad_election(self):
        response = self.app.get(
            '/election/2014/constituencies/declared',
            expect_errors=True
        )

        self.assertEqual(response.status_code, 404)

    def test_constituencies_appear_when_declared(self):
        response = self.app.get(
            '/election/2015/constituencies/declared'
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(
            re.search(
                r'''(?ms)<del><a[^>]*>Dulwich and West Norwood''',
                response.text
            )
        )
        self.assertTrue(
            re.search(
                r'''(?ms)<a[^>]*>Camberwell and Peckham''',
                response.text
            )
        )
        self.assertFalse(
            re.search(
                r'''(?ms)<del><a[^>]*>Camberwell and Peckham''',
                response.text
            )
        )
        response.mustcontain('1 still undeclared (50% done)')

        unelected = MembershipExtra.objects.filter(
            election=self.election,
            base__person_id=2010,
            base__post__extra__slug='65913'
        ).first()

        unelected.elected = True
        unelected.save()

        response = self.app.get(
            '/election/2015/constituencies/declared'
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(
            re.search(
                r'''(?ms)<del><a[^>]*>Dulwich and West Norwood''',
                response.text
            )
        )
        self.assertTrue(
            re.search(
                r'''(?ms)<del><a[^>]*>Camberwell and Peckham''',
                response.text
            )
        )
        response.mustcontain('0 still undeclared (100% done)')
