from django.test import TestCase

from ..models import PopItPerson
from ..csv_helpers import list_to_csv
from fake_popit import get_example_popit_json


class CSVTests(TestCase):
    def setUp(self):
        # The second person's name (and party name) have diacritics in
        # them to test handling of Unicode when outputting to CSV.
        self.people = [
            PopItPerson.create_from_dict(
                get_example_popit_json(person_json_filename)['result']
            )
            for person_json_filename in
            (
                'persons_2009_embed=membership.organization.json',
                'persons-1953_embed=membership.organization.json',
            )
        ]

    def test_as_dict(self):
        person_dict = self.people[0].as_dict('2015')
        self.assertEqual(len(person_dict), 30)
        self.assertEqual(person_dict['id'], "2009")

    def test_as_dict_2010(self):
        # Could do with a person example who changes constituency
        person_dict = self.people[0].as_dict('2010')
        self.assertEqual(len(person_dict), 30)
        self.assertEqual(person_dict['id'], "2009")

    def test_csv_output(self):
        example_output = \
            'id,name,honorific_prefix,honorific_suffix,gender,birth_date,election,party_id,party_name,post_id,post_label,mapit_url,elected,email,twitter_username,facebook_page_url,party_ppc_page_url,facebook_personal_url,homepage_url,wikipedia_url,linkedin_url,image_url,proxy_image_url_template,image_copyright,image_uploading_user,image_uploading_user_notes,gss_code,parlparse_id,theyworkforyou_url,party_ec_id\r\n' \
            '2009,Tessa Jowell,Ms,DBE,female,,2015,party:53,Labour Party,65808,Dulwich and West Norwood,http://mapit.mysociety.org/area/65808,,jowell@example.com,,,,,,,,,,,,,E14000673,uk.org.publicwhip/person/10326,http://www.theyworkforyou.com/mp/10326,\r\n' \
            '1953,Daith\xc3\xad McKay,,,male,,2015,party:39,Sinn F\xc3\xa9in,66135,North Antrim,http://mapit.mysociety.org/area/66135,,,,,,,,,,,,,,,N06000012,,,PP39\r\n'
        self.assertEqual(
            list_to_csv([p.as_dict('2015') for p in self.people]),
            example_output,
        )
