# -*- coding: utf-8 -*-

from __future__ import unicode_literals

from datetime import datetime
from io import BytesIO

from django_webtest import WebTest

from lxml import etree

from django.utils import timezone
from django.utils.feedgenerator import rfc3339_date

from candidates.tests import factories

from candidates.tests.auth import TestUserMixin
from .models import ResultEvent


class TestResultsFeed(TestUserMixin, WebTest):

    maxDiff = None

    def compare_xml(self, xml_a, xml_b):
        """Compare two XML strings under XML canonicalization

        This is insensitive to attribute order; if there is a
        different, self.assertEqual is used to generate the usual
        unequal test output, which has a helpful diff.

        This approach was suggested in:

            http://stackoverflow.com/a/12430650/223092
        """
        parser = etree.XMLParser(remove_blank_text=True)
        tree_a = etree.fromstring(xml_a, parser)
        tree_b = etree.fromstring(xml_b, parser)
        c14n_a = BytesIO()
        c14n_b = BytesIO()
        tree_a.getroottree().write_c14n(c14n_a)
        tree_b.getroottree().write_c14n(c14n_b)
        if c14n_a.getvalue() != c14n_b.getvalue():
            self.assertEqual(xml_a, xml_b)

    def setUp(self):
        wmc_area_type = factories.AreaTypeFactory.create()
        person_extra = factories.PersonExtraFactory.create(
            base__id='4322',
            base__name='Tessa Jowell'
        )
        election = factories.ElectionFactory.create(
            slug='2015',
            name='2015 General Election',
            area_types=(wmc_area_type,),
        )
        factories.PartyExtraFactory.create(
            slug='party:53',
            base__name='Labour Party',
        )
        result_event = ResultEvent.objects.create(
            election=election,
            winner=person_extra.base,
            winner_person_name=person_extra.base.name,
            post_id='65808',
            post_name='Member of Parliament for Dulwich and West Norwood',
            winner_party_id='party:53',
            source='Seen on the BBC news',
            user=self.user,
            parlparse_id='uk.org.publicwhip/person/123456',
        )
        result_event.created = datetime(2015, 12, 1, 15, 59)

    def test_all_feed_with_one_item(self):
        response = self.app.get('/results/all.atom')
        root = etree.XML(response.content)
        xml_pretty = etree.tounicode(root, pretty_print=True)

        result_event = ResultEvent.objects.first()
        expected = '''<feed xmlns="http://www.w3.org/2005/Atom" xml:lang="en-gb">
  <title>Election results from example.com (with extra data)</title>
  <link href="http://example.com/" rel="alternate"/>
  <link href="http://example.com/results/all.atom" rel="self"/>
  <id>http://example.com/</id>
  <updated>{updated}</updated>
  <entry>
    <title>Tessa Jowell (Labour Party) won in Member of Parliament for Dulwich and West Norwood</title>
    <link href="http://example.com/#{item_id}" rel="alternate"/>
    <published>{updated}</published>
    <updated>{updated}</updated>
    <author>
      <name>john</name>
    </author>
    <id>http://example.com/#{item_id}</id>
    <summary type="html">A example.com volunteer recorded at {space_separated} that Tessa Jowell (Labour Party) won the ballot in Member of Parliament for Dulwich and West Norwood, quoting the source 'Seen on the BBC news').</summary>
    <post_id>65808</post_id>
    <winner_person_id>4322</winner_person_id>
    <winner_person_name>Tessa Jowell</winner_person_name>
    <winner_party_id>party:53</winner_party_id>
    <winner_party_name>Labour Party</winner_party_name>
    <user_id>{user_id}</user_id>
    <post_name>Member of Parliament for Dulwich and West Norwood</post_name>
    <information_source>Seen on the BBC news</information_source>
    <parlparse_id>uk.org.publicwhip/person/123456</parlparse_id>
  </entry>
</feed>
'''.format(
    updated=rfc3339_date(result_event.created),
    space_separated=result_event.created.strftime("%Y-%m-%d %H:%M:%S"),
    item_id=result_event.id,
    user_id=self.user.id,
)
        self.compare_xml(expected, xml_pretty)

    def test_all_basic_feed_with_one_item(self):
        response = self.app.get('/results/all-basic.atom')
        root = etree.XML(response.content)
        xml_pretty = etree.tounicode(root, pretty_print=True)

        result_event = ResultEvent.objects.first()
        expected = '''<feed xmlns="http://www.w3.org/2005/Atom" xml:lang="en-gb">
  <title>Election results from example.com</title>
  <link href="http://example.com/" rel="alternate"/>
  <link href="http://example.com/results/all-basic.atom" rel="self"/>
  <id>http://example.com/</id>
  <updated>{updated}</updated>
  <entry>
    <title>Tessa Jowell (Labour Party) won in Member of Parliament for Dulwich and West Norwood</title>
    <link href="http://example.com/#{item_id}" rel="alternate"/>
    <published>{updated}</published>
    <updated>{updated}</updated>
    <author>
      <name>john</name>
    </author>
    <id>http://example.com/#{item_id}</id>
    <summary type="html">A example.com volunteer recorded at {space_separated} that Tessa Jowell (Labour Party) won the ballot in Member of Parliament for Dulwich and West Norwood, quoting the source 'Seen on the BBC news').</summary>
  </entry>
</feed>
'''.format(
    updated=rfc3339_date(result_event.created),
    space_separated=result_event.created.strftime("%Y-%m-%d %H:%M:%S"),
    item_id=result_event.id,
)
        self.compare_xml(expected, xml_pretty)
