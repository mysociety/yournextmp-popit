from mock import patch
from os.path import join, realpath, dirname

from django_webtest import WebTest
from webtest import Upload

from django.core.urlresolvers import reverse

from candidates.tests.auth import TestUserMixin
from candidates.tests.fake_popit import FakePostCollection

from official_documents.models import OfficialDocument

TEST_MEDIA_ROOT=realpath(
    join(
        dirname(__file__), '..', '..',
        'moderation_queue', 'tests', 'media'
    )
)

# FIXME: it's probably best not to include anything from the
# candidates application in here so that official_documents is
# standalone, so we should at some point replace TestUserMixin with
# creating appropriate users here, and the parts of the tests that
# check whether the upload text appears correctly should be moved to
# the candidates application tests.

@patch('candidates.popit.PopIt')
class TestModels(TestUserMixin, WebTest):

    mapit_id = '65808'

    def test_upload_unauthorized(self, mock_popit):
        mock_popit.return_value.posts = FakePostCollection
        response = self.app.get(
            '/constituency/65808/dulwich-and-west-norwood',
            user=self.user
        )
        csrftoken = self.app.cookies['csrftoken']
        upload_url = reverse(
            'upload_document_view',
            kwargs={'mapit_id': self.mapit_id}
        )
        image_filename = join(TEST_MEDIA_ROOT, 'pilot.jpg')
        with open(image_filename) as f:
            response = self.app.post(
                upload_url,
                {
                    'csrfmiddlewaretoken': csrftoken,
                    'mapit_id': self.mapit_id,
                    'document_type': OfficialDocument.NOMINATION_PAPER,
                    'source_url': 'http://example.org/foo',
                    '': Upload('pilot.jpg', f.read())
                },
                user=self.user,
                expect_errors=True,
            )
        self.assertEqual(response.status_code, 403)
        self.assertIn(
            'You must be in the member of a particular group in order to view that page',
            unicode(response)
        )

    def test_upload_authorized(self, mock_popit):
        mock_popit.return_value.posts = FakePostCollection
        response = self.app.get(
            '/constituency/65808/dulwich-and-west-norwood',
            user=self.user_who_can_upload_documents
        )
        self.assertIn(
            'as you have permission to upload documents',
            unicode(response)
        )
        response = self.app.get(
            reverse('upload_document_view', args=(self.mapit_id,)),
            user=self.user_who_can_upload_documents,
        )
        form = response.forms['document-upload-form']
        form['source_url'] = 'http://example.org/foo'
        image_filename = join(TEST_MEDIA_ROOT, 'pilot.jpg')
        with open(image_filename) as f:
            form['uploaded_file'] = Upload('pilot.jpg', f.read())
        form.submit()
        self.assertEqual(response.status_code, 200)
        ods = OfficialDocument.objects.all()
        self.assertEqual(ods.count(), 1)
        od = ods[0]
        self.assertEqual(od.source_url, 'http://example.org/foo')
        self.assertEqual(od.mapit_id, '65808')
