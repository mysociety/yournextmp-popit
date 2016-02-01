from __future__ import unicode_literals

import json

from django.utils.six.moves.urllib_parse import urlsplit

from django_webtest import WebTest

from popolo.models import Person

from .auth import TestUserMixin
from ..models import LoggedAction

from .factories import (
    AreaTypeFactory, ElectionFactory, ParliamentaryChamberFactory,
    PartyFactory, PartyExtraFactory, PostExtraFactory, PartySetFactory
)


class TestNewPersonView(TestUserMixin, WebTest):

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
        # Just a smoke test for the moment:
        response = self.app.get(
            '/constituency/65808/dulwich-and-west-norwood',
            user=self.user_refused
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

    def test_new_person_submission(self):
        response = self.app.get(
            '/election/2015/post/65808/dulwich-and-west-norwood',
            user=self.user,
        )
        form = response.forms['new-candidate-form']
        form['name'] = 'Elizabeth Bennet'
        form['email'] = 'lizzie@example.com'
        form['party_gb_2015'] = self.parties['party:53'].base_id
        form['wikipedia_url'] = 'http://en.wikipedia.org/wiki/Lizzie_Bennet'
        submission_response = form.submit()

        # If there's no source specified, it shouldn't ever get to
        # update_person, and redirect back to the constituency page:
        self.assertEqual(submission_response.status_code, 200)

        self.assertContains(
            submission_response,
            'You must indicate how you know about this candidate'
        )

        form['source'] = 'Testing adding a new person to a post'
        submission_response = form.submit()

        person = Person.objects.get(name='Elizabeth Bennet')

        self.assertEqual(person.birth_date, '')

        self.assertEqual(submission_response.status_code, 302)
        self.assertEqual(
            submission_response.location,
            'http://localhost:80/person/{0}'.format(person.id)
        )

        self.assertEqual(person.name, 'Elizabeth Bennet')
        self.assertEqual(person.email, 'lizzie@example.com')

        self.assertEqual(person.memberships.count(), 1)

        candidacy = person.memberships.first()

        self.assertEqual(candidacy.post.extra.slug, '65808')
        self.assertEqual(candidacy.role, 'Candidate')
        self.assertEqual(candidacy.on_behalf_of.extra.slug, 'party:53')
        self.assertEqual(candidacy.extra.election_id, self.election.id)

        links = person.links.all()
        self.assertEqual(links.count(), 1)
        self.assertEqual(links[0].url, 'http://en.wikipedia.org/wiki/Lizzie_Bennet')

        self.assertNotEqual(person.extra.versions, '[]')

        versions = json.loads(person.extra.versions)
        self.assertEqual(len(versions), 1)
        self.assertEqual(versions[0]['information_source'],
                         'Testing adding a new person to a post')

        last_logged_action = LoggedAction.objects.all().order_by('-created')[0]
        self.assertEqual(
            last_logged_action.person_id,
            person.id,
        )
        self.assertEqual(
            last_logged_action.action_type,
            'person-create'
        )
