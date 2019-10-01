from __future__ import unicode_literals

import codecs
from io import BytesIO
from mock import patch
import os

from datetime import datetime, timedelta

from django_webtest import WebTest
from django.test import TestCase

from lxml import etree

from candidates.models import LoggedAction, PersonExtra

from . import factories
from .auth import TestUserMixin
from .test_version_diffs import tidy_html_whitespace


def random_person_id():
    return codecs.encode(os.urandom(8), 'hex').decode()


def change_updated_and_created(la, timestamp):
    # auto_add_now and auto_now are used for the LoggedAction created
    # and updated fields, which are awkward to override. You can do
    # this, however, by use the update() method of QuerySet, which is
    # converted directly to an SQL UPDATE and doesn't trigger
    # save-related signals.
    LoggedAction.objects.filter(pk=la.pk).update(
        created=timestamp, updated=timestamp)


def canonicalize_xml(xml_bytes):
    parsed = etree.fromstring(xml_bytes)
    out = BytesIO()
    parsed.getroottree().write_c14n(out)
    return out.getvalue()


def fake_diff_html(self, version_id, inline_style=False):
    return '<div{0}>Fake diff</div>'.format(
        ' style="color: red"' if inline_style else ''
    )


@patch.object(PersonExtra, 'diff_for_version', fake_diff_html)
@patch('candidates.models.db.datetime')
class TestNeedsReview(TestUserMixin, WebTest):

    maxDiff = None

    def setUp(self):
        super(TestNeedsReview, self).setUp()
        self.current_datetime = datetime(2017, 5, 2, 18, 10, 5, 0)
        # Reuse existing users created in TestUserMixin:
        for username, u in (
                ('lapsed_experienced', self.user),
                ('new_suddenly_lots', self.user_who_can_merge),
                ('new_only_one', self.user_who_can_upload_documents),
                ('morbid_vandal', self.user_who_can_lock)):
            u.username = username
            u.save()
            setattr(self, username, u)

        example_person = factories.PersonExtraFactory.create(
            base__id='2009',
            base__name='Tessa Jowell',
        ).base

        # Create old edits for the experienced user:
        date_ages_ago = self.current_datetime - timedelta(days=365)
        for i in range(20):
            la = LoggedAction.objects.create(
                id=(1000 + i),
                user=self.lapsed_experienced,
                action_type='person-update',
                person=example_person,
                popit_person_new_version=random_person_id(),
                source='Just for tests...',
            )
            dt = date_ages_ago - timedelta(minutes=i*10)
            change_updated_and_created(la, dt)
        # ... and a couple of new edits for the experienced user:
        for i in range(2):
            la = LoggedAction.objects.create(
                id=(1500 + i),
                user=self.lapsed_experienced,
                action_type='person-update',
                person=example_person,
                popit_person_new_version=random_person_id(),
                source='Just for tests...',
            )
            dt = self.current_datetime - timedelta(minutes=i*5)
            change_updated_and_created(la, dt)

        # Create lots of very recent edits for a new user:
        for i in range(10):
            la = LoggedAction.objects.create(
                id=(2000 + i),
                user=self.new_suddenly_lots,
                action_type='person-update',
                person=example_person,
                popit_person_new_version=random_person_id(),
                source='Just for tests',
            )
            dt = self.current_datetime - timedelta(minutes=i*7)
            change_updated_and_created(la, dt)

        # Create a single recent edit for a new user:
        la = LoggedAction.objects.create(
            id=(2500 + i),
            user=self.new_only_one,
            action_type='person-update',
            person=example_person,
            popit_person_new_version=random_person_id(),
            source='Just for tests',
        )
        dt = self.current_datetime - timedelta(minutes=2)
        change_updated_and_created(la, dt)

        # Create a candidate with a death date, and edit of that
        # candidate:
        dead_person = factories.PersonExtraFactory.create(
            base__id='7448',
            base__name='The Eurovisionary Ronnie Carroll',
            base__birth_date='1934-08-18',
            base__death_date='2015-04-13'
        ).base
        la = LoggedAction.objects.create(
            id=3000,
            user=self.morbid_vandal,
            action_type='person-update',
            person=dead_person,
            popit_person_new_version=random_person_id(),
            source='Just for tests',
            updated=dt,
            created=dt,
        )
        dt = self.current_datetime - timedelta(minutes=4)
        change_updated_and_created(la, dt)

        prime_minister = factories.PersonExtraFactory.create(
            base__id='2811',
            base__name='Theresa May',
            marked_for_review=True,
        ).base
        # Create a candidate on the "liable to vandalism" list.
        la = LoggedAction.objects.create(
            id=4000,
            user=self.lapsed_experienced,
            action_type='person-update',
            person=prime_minister,
            popit_person_new_version=random_person_id(),
            source='Just for tests...',
        )
        dt = self.current_datetime - timedelta(minutes=33)
        change_updated_and_created(la, dt)

        # Create a photo-upload action - this should not be included:
        la = LoggedAction.objects.create(
            id=4500,
            user=self.lapsed_experienced,
            action_type='photo-upload',
            person=example_person,
            popit_person_new_version=random_person_id(),
            source='Just for tests...',
        )
        dt = self.current_datetime - timedelta(minutes=41)
        change_updated_and_created(la, dt)

        # Let's say a new user is has locked a constituency - this is
        # a useful test because (because of a bug) locked
        # constituencies have neither a post nor a person set:
        la = LoggedAction.objects.create(
            id=5000,
            user=self.morbid_vandal,
            action_type='constituency-lock',
            person=None,
            post=None,
            popit_person_new_version='',
            source='Testing no post and no person'
        )
        dt = self.current_datetime - timedelta(minutes=13)
        change_updated_and_created(la, dt)

    def test_needs_review_as_expected(self, mock_datetime):
        mock_datetime.now.return_value = self.current_datetime
        needs_review_dict = LoggedAction.objects.in_recent_days(5).needs_review()
        # Here we're expecting the following LoggedActions to be picked out:
        #    1 edit of a dead candidate (by 'morbid_vandal'
        #    3 edits from 'new_suddenly_lots' (we just consider the first
        #      three edits from a new user needs_review)
        #    1 first edit from 'new_only_one'
        #    1 edit from a user who was mostly active in the past to the
        #      prime minister's record
        #    1 constituency-lock from a new user
        self.assertEqual(len(needs_review_dict), 1 + 3 + 1 + 1 + 1)
        results = [
            (la.user.username, la.action_type, reasons)
            for la, reasons in
            sorted(needs_review_dict.items(), key=lambda t: t[0].created)
        ]
        self.assertEqual(
            results,
            [('new_suddenly_lots',
              'person-update',
              ['One of the first 3 edits of user new_suddenly_lots']),
             ('new_suddenly_lots',
              'person-update',
              ['One of the first 3 edits of user new_suddenly_lots']),
             ('new_suddenly_lots',
              'person-update',
              ['One of the first 3 edits of user new_suddenly_lots']),
             ('lapsed_experienced',
              'person-update',
              ['Edit of a candidate whose record may be particularly liable to vandalism']),
             (u'morbid_vandal',
              u'constituency-lock',
              [u'One of the first 3 edits of user morbid_vandal']),
             ('morbid_vandal',
              'person-update',
              ['One of the first 3 edits of user morbid_vandal',
               'Edit of a candidate who has died']),
             ('new_only_one',
              'person-update',
              ['One of the first 3 edits of user new_only_one'])])

    def test_xml_feed(self, mock_datetime):
        mock_datetime.now.return_value = self.current_datetime
        response = self.app.get('/feeds/needs-review.xml')
        got = canonicalize_xml(response.content)
        expected = \
            b'<feed xmlns="http://www.w3.org/2005/Atom" xml:lang="en-gb">' \
            b'<title>example.com changes for review</title>' \
            b'<link href="http://example.com/feeds/needs-review.xml" rel="alternate"></link>' \
            b'<link href="http://example.com/feeds/needs-review.xml" rel="self"></link>' \
            b'<id>http://example.com/feeds/needs-review.xml</id>' \
            b'<updated>2017-05-02T17:08:05+00:00</updated>' \
            b'<entry><title>Tessa Jowell (2009) - person-update</title><link href="http://example.com/person/2009" rel="alternate"></link><updated>2017-05-02T17:08:05+00:00</updated>' \
            b'<author><name>new_only_one</name></author><id>needs-review:2509</id>' \
            b'<summary type="html">&lt;p&gt;person-update of &lt;a href="/person/2009"&gt;Tessa Jowell (2009)&lt;/a&gt; by new_only_one with source: \xe2\x80\x9c Just for tests \xe2\x80\x9d;&lt;/p&gt;\n&lt;ul&gt;\n&lt;li&gt;One of the first 3 edits of user new_only_one&lt;/li&gt;\n&lt;/ul&gt;&lt;/p&gt;&lt;div style="color: red"&gt;Fake diff&lt;/div&gt;</summary></entry>' \
            b'<entry><title>The Eurovisionary Ronnie Carroll (7448) - person-update</title><link href="http://example.com/person/7448" rel="alternate"></link><updated>2017-05-02T17:06:05+00:00</updated>' \
            b'<author><name>morbid_vandal</name></author><id>needs-review:3000</id>' \
            b'<summary type="html">&lt;p&gt;person-update of &lt;a href="/person/7448"&gt;The Eurovisionary Ronnie Carroll (7448)&lt;/a&gt; by morbid_vandal with source: \xe2\x80\x9c Just for tests \xe2\x80\x9d;&lt;/p&gt;\n&lt;ul&gt;\n&lt;li&gt;One of the first 3 edits of user morbid_vandal&lt;/li&gt;\n&lt;li&gt;Edit of a candidate who has died&lt;/li&gt;\n&lt;/ul&gt;&lt;/p&gt;&lt;div style="color: red"&gt;Fake diff&lt;/div&gt;</summary></entry>' \
            b'<entry><title>constituency-lock</title><link href="http://example.com/" rel="alternate"></link><updated>2017-05-02T16:57:05+00:00</updated>' \
            b'<author><name>morbid_vandal</name></author><id>needs-review:5000</id>' \
            b'<summary type="html">&lt;p&gt;constituency-lock of  by morbid_vandal with source: \xe2\x80\x9c Testing no post and no person \xe2\x80\x9d;&lt;/p&gt;\n&lt;ul&gt;\n&lt;li&gt;One of the first 3 edits of user morbid_vandal&lt;/li&gt;\n&lt;/ul&gt;&lt;/p&gt;</summary></entry>' \
            b'<entry><title>Theresa May (2811) - person-update</title><link href="http://example.com/person/2811" rel="alternate"></link><updated>2017-05-02T16:37:05+00:00</updated>' \
            b'<author><name>lapsed_experienced</name></author><id>needs-review:4000</id>' \
            b'<summary type="html">&lt;p&gt;person-update of &lt;a href="/person/2811"&gt;Theresa May (2811)&lt;/a&gt; by lapsed_experienced with source: \xe2\x80\x9c Just for tests... \xe2\x80\x9d;&lt;/p&gt;\n&lt;ul&gt;\n&lt;li&gt;Edit of a candidate whose record may be particularly liable to vandalism&lt;/li&gt;\n&lt;/ul&gt;&lt;/p&gt;&lt;div style="color: red"&gt;Fake diff&lt;/div&gt;</summary></entry>' \
            b'<entry><title>Tessa Jowell (2009) - person-update</title><link href="http://example.com/person/2009" rel="alternate"></link><updated>2017-05-02T16:21:05+00:00</updated>' \
            b'<author><name>new_suddenly_lots</name></author><id>needs-review:2007</id>' \
            b'<summary type="html">&lt;p&gt;person-update of &lt;a href="/person/2009"&gt;Tessa Jowell (2009)&lt;/a&gt; by new_suddenly_lots with source: \xe2\x80\x9c Just for tests \xe2\x80\x9d;&lt;/p&gt;\n&lt;ul&gt;\n&lt;li&gt;One of the first 3 edits of user new_suddenly_lots&lt;/li&gt;\n&lt;/ul&gt;&lt;/p&gt;&lt;div style="color: red"&gt;Fake diff&lt;/div&gt;</summary></entry>' \
            b'<entry><title>Tessa Jowell (2009) - person-update</title><link href="http://example.com/person/2009" rel="alternate"></link><updated>2017-05-02T16:14:05+00:00</updated>' \
            b'<author><name>new_suddenly_lots</name></author><id>needs-review:2008</id>' \
            b'<summary type="html">&lt;p&gt;person-update of &lt;a href="/person/2009"&gt;Tessa Jowell (2009)&lt;/a&gt; by new_suddenly_lots with source: \xe2\x80\x9c Just for tests \xe2\x80\x9d;&lt;/p&gt;\n&lt;ul&gt;\n&lt;li&gt;One of the first 3 edits of user new_suddenly_lots&lt;/li&gt;\n&lt;/ul&gt;&lt;/p&gt;&lt;div style="color: red"&gt;Fake diff&lt;/div&gt;</summary></entry>' \
            b'<entry><title>Tessa Jowell (2009) - person-update</title><link href="http://example.com/person/2009" rel="alternate"></link><updated>2017-05-02T16:07:05+00:00</updated>' \
            b'<author><name>new_suddenly_lots</name></author><id>needs-review:2009</id>' \
            b'<summary type="html">&lt;p&gt;person-update of &lt;a href="/person/2009"&gt;Tessa Jowell (2009)&lt;/a&gt; by new_suddenly_lots with source: \xe2\x80\x9c Just for tests \xe2\x80\x9d;&lt;/p&gt;\n&lt;ul&gt;\n&lt;li&gt;One of the first 3 edits of user new_suddenly_lots&lt;/li&gt;\n&lt;/ul&gt;&lt;/p&gt;&lt;div style="color: red"&gt;Fake diff&lt;/div&gt;</summary></entry></feed>'
        self.assertEqual(got, expected)


class TestDiffHTML(TestCase):

    def test_missing_version(self):
        person = factories.PersonExtraFactory.create(
            base__name='John Smith',
            base__id='1234567',
            versions='[]',
        ).base
        la = LoggedAction.objects.create(
            person=person,
            popit_person_new_version='1376abcd9234')
        self.assertEqual(
            la.diff_html,
            '<p>Couldn&#39;t find version 1376abcd9234 for person with ID '
            '1234567</p>'
        )

    def test_found_version(self):
        person = factories.PersonExtraFactory.create(
            base__name='Sarah Jones',
            base__id='1234567',
            versions='''[{
                "data": {
                    "honorific_prefix": "Mrs",
                    "honorific_suffix": "",
                    "id": "6704",
                    "identifiers": [{"id": "552f80d0ed1c6ee164eeae51",
                    "identifier": "13445",
                    "scheme": "yournextmp-candidate"}],
                    "image": null,
                    "linkedin_url": "",
                    "name": "Sarah Jones",
                    "party_ppc_page_url": "",
                    "proxy_image": null,
                    "twitter_username": "",
                    "wikipedia_url": ""
                },
                "information_source": "Made up 2",
                "timestamp": "2015-05-08T01:52:27.061038",
                "username": "test",
                "version_id": "3fc494d54f61a157"
            },
            {
                "data": {
                    "email": "sarah@example.com",
                    "honorific_prefix": "Mrs",
                    "honorific_suffix": "",
                    "id": "6704",
                    "identifiers": [{
                        "id": "5477866f737edc5252ce5938",
                        "identifier": "13445",
                        "scheme": "yournextmp-candidate"
                    }],
                    "image": null,
                    "linkedin_url": "",
                    "name": "Sarah Jones",
                    "party_ppc_page_url": "",
                    "proxy_image": null,
                    "twitter_username": "",
                    "wikipedia_url": ""
                },
                "information_source": "Made up 1",
                "timestamp": "2015-03-10T05:35:15.297559",
                "username": "test",
                "version_id": "2f07734529a83242"
            }]''',
        ).base
        la = LoggedAction.objects.create(
            person=person,
            popit_person_new_version='3fc494d54f61a157')
        self.assertEqual(
            tidy_html_whitespace(la.diff_html),
            '<dl><dt>Changes made compared to parent 2f07734529a83242</dt>'
            '<dd><p class="version-diff">'
            '<span class="version-op-remove" style="color: #8e2424">'
            'Removed: email (previously it was &quot;sarah@example.com&quot;)'
            '</span><br/></p></dd></dl>'
        )
