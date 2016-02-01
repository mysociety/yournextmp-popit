from __future__ import unicode_literals

import re

from django.test import TestCase

from candidates.views.people import get_call_to_action_flash_message

from . import factories

def normalize_whitespace(s):
    return re.sub(r'(?ms)\s+', ' ', s)

class TestGetFlashMessage(TestCase):

    maxDiff = None

    def setUp(self):
        election = factories.ElectionFactory.create(
            slug='2015',
            name='2015 General Election',
        )
        earlier_election = factories.EarlierElectionFactory.create(
            slug='2010',
            name='2010 General Election',
        )
        commons = factories.ParliamentaryChamberFactory.create()
        self.fake_person_extra = factories.PersonExtraFactory.create(
            base__name='Wreck-it-Ralph',
            base__id=42,
        )
        post_extra_in_2010 = factories.PostExtraFactory.create(
            elections=(election, earlier_election),
            slug='14419',
            base__label='Member of Parliament for Edinburgh East',
            base__organization=commons,
        )
        post_extra_in_2015 = factories.PostExtraFactory.create(
            elections=(election, earlier_election),
            slug='14420',
            base__label='Member of Parliament for Edinburgh North and Leith',
            base__organization=commons,
        )
        factories.CandidacyExtraFactory.create(
            election=election,
            base__person=self.fake_person_extra.base,
            base__post=post_extra_in_2010.base,
        )
        factories.CandidacyExtraFactory.create(
            election=earlier_election,
            base__person=self.fake_person_extra.base,
            base__post=post_extra_in_2015.base,
        )

    def test_get_flash_message_new_person(self):
        self.assertEqual(
            ' Thank-you for adding <a href="/person/42">Wreck-it-Ralph</a>! '
            'Now you can carry on to:'
            ' <ul> <li> <a href="/person/42/update">Edit Wreck-it-Ralph again</a> </li>'
            ' <li> Add a candidate for <a href="/numbers/attention-needed">one '
            'of the posts with fewest candidates</a> </li>'
            ' <li> <a href="/election/2015/person/create/">Add another '
            'candidate in the 2015 General Election</a> </li> </ul> ',
            normalize_whitespace(
                get_call_to_action_flash_message(
                    self.fake_person_extra.base,
                    new_person=True
                )
            )
        )

    def test_get_flash_message_updated_person(self):
        self.assertEqual(
            ' Thank-you for updating <a href="/person/42">Wreck-it-Ralph</a>! '
            'Now you can carry on to:'
            ' <ul> <li> <a href="/person/42/update">Edit Wreck-it-Ralph again</a> </li>'
            ' <li> Add a candidate for <a href="/numbers/attention-needed">one '
            'of the posts with fewest candidates</a> </li>'
            ' <li> <a href="/election/2015/person/create/">Add another '
            'candidate in the 2015 General Election</a> </li> </ul> ',
            normalize_whitespace(
                get_call_to_action_flash_message(
                    self.fake_person_extra.base,
                    new_person=False
                )
            )
        )
