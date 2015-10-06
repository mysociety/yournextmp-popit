import re

from django.test import TestCase

from candidates.models.popit import PopItPerson
from candidates.views.people import get_call_to_action_flash_message

def normalize_whitespace(s):
    return re.sub(r'(?ms)\s+', ' ', s)

class TestGetFlashMessage(TestCase):

    maxDiff = None

    def setUp(self):
        self.fake_person = PopItPerson.create_from_dict(
            {
                'name': 'Wreck-it-Ralph',
                'id': 42,
            }
        )
        self.fake_person.standing_in = {
            '2010': {
               'name': 'Edinburgh East',
               'post_id': '14419',
               'mapit_url': 'http://mapit.mysociety.org/area/14419',
            },
            '2015': {
               'name': 'Edinburgh North and Leith',
               'post_id': '14420',
               'mapit_url': 'http://mapit.mysociety.org/area/14420',
            }
        }

    def test_get_flash_message_new_person(self):
        self.assertEqual(
            u' Thank-you for adding <a href="/person/42">Wreck-it-Ralph</a>! '
            u'Now you can carry on to:'
            u' <ul> <li> <a href="/person/42/update">Edit Wreck-it-Ralph again</a> </li>'
            u' <li> Add a candidate for <a href="/numbers/attention-needed">one '
            u'of the posts with fewest candidates</a> </li>'
            u' <li> <a href="/election/2015/person/create/">Add another '
            u'candidate in the 2015 General Election</a> </li> </ul> ',
            normalize_whitespace(
                get_call_to_action_flash_message(self.fake_person, new_person=True)
            )
        )

    def test_get_flash_message_updated_person(self):
        self.assertEqual(
            u' Thank-you for updating <a href="/person/42">Wreck-it-Ralph</a>! '
            u'Now you can carry on to:'
            u' <ul> <li> <a href="/person/42/update">Edit Wreck-it-Ralph again</a> </li>'
            u' <li> Add a candidate for <a href="/numbers/attention-needed">one '
            u'of the posts with fewest candidates</a> </li>'
            u' <li> <a href="/election/2015/person/create/">Add another '
            u'candidate in the 2015 General Election</a> </li> </ul> ',
            normalize_whitespace(
                get_call_to_action_flash_message(self.fake_person, new_person=False)
            )
        )
