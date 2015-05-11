from mock import patch

from django_webtest import WebTest

from .auth import TestUserMixin
from .fake_popit import (FakePersonCollection, FakeOrganizationCollection,
                         FakePostCollection)

@patch('candidates.popit.PopIt')
class TestConstituencyDetailView(TestUserMixin, WebTest):

    def test_any_constituency_page_without_login(self, mock_popit):
        mock_popit.return_value.organizations = FakeOrganizationCollection
        mock_popit.return_value.persons = FakePersonCollection
        mock_popit.return_value.posts = FakePostCollection

        # Just a smoke test for the moment:
        response = self.app.get('/constituency/65808/dulwich-and-west-norwood')
        response.mustcontain('<a href="/person/2009/tessa-jowell" class="candidate-name">Tessa Jowell</a> <span class="party">Labour Party</span>')
        # There should be no forms on the page if you're not logged in:

        self.assertEqual(0, len(response.forms))

    def test_any_constituency_page(self, mock_popit):
        mock_popit.return_value.organizations = FakeOrganizationCollection
        mock_popit.return_value.persons = FakePersonCollection
        mock_popit.return_value.posts = FakePostCollection

        # Just a smoke test for the moment:
        response = self.app.get(
            '/constituency/65808/dulwich-and-west-norwood',
            user=self.user
        )
        response.mustcontain('<a href="/person/2009/tessa-jowell" class="candidate-name">Tessa Jowell</a> <span class="party">Labour Party</span>')
        form = response.forms['new-candidate-form']
        self.assertTrue(form)
