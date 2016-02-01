from __future__ import unicode_literals

from os.path import join, realpath, dirname

from django_webtest import WebTest
from webtest import Upload

from django.core.urlresolvers import reverse

from candidates.tests.auth import TestUserMixin

from official_documents.models import OfficialDocument

from candidates.tests.factories import (
    AreaTypeFactory, ElectionFactory, ParliamentaryChamberFactory,
    PostExtraFactory, PartySetFactory
)

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

class TestModels(TestUserMixin, WebTest):

    def setUp(self):
        wmc_area_type = AreaTypeFactory.create()
        gb_parties = PartySetFactory.create(slug='gb', name='Great Britain')
        election = ElectionFactory.create(
            slug='2015',
            name='2015 General Election',
            area_types=(wmc_area_type,)
        )
        commons = ParliamentaryChamberFactory.create()
        self.post_extra = PostExtraFactory.create(
            elections=(election,),
            base__organization=commons,
            slug='65808',
            base__label='Member of Parliament for Dulwich and West Norwood',
            party_set=gb_parties,
        )

    def test_upload_unauthorized(self):
        response = self.app.get(
            '/election/2015/post/65808/dulwich-and-west-norwood',
            user=self.user
        )
        csrftoken = self.app.cookies['csrftoken']
        upload_url = reverse(
            'upload_document_view',
            kwargs={'election': '2015', 'post_id': self.post_extra.slug}
        )
        image_filename = join(TEST_MEDIA_ROOT, 'pilot.jpg')
        with open(image_filename, 'rb') as f:
            response = self.app.post(
                upload_url,
                {
                    'csrfmiddlewaretoken': csrftoken,
                    'post_id': self.post_extra.slug,
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
            response.text
        )

    def test_upload_authorized(self):
        response = self.app.get(
            '/election/2015/post/65808/dulwich-and-west-norwood',
            user=self.user_who_can_upload_documents
        )
        self.assertIn(
            'As you have permission to upload documents',
            response.text
        )
        response = self.app.get(
            reverse('upload_document_view', args=('2015', self.post_extra.slug)),
            user=self.user_who_can_upload_documents,
        )
        form = response.forms['document-upload-form']
        form['source_url'] = 'http://example.org/foo'
        image_filename = join(TEST_MEDIA_ROOT, 'pilot.jpg')
        with open(image_filename, 'rb') as f:
            form['uploaded_file'] = Upload('pilot.jpg', f.read())
        form.submit()
        self.assertEqual(response.status_code, 200)
        ods = OfficialDocument.objects.all()
        self.assertEqual(ods.count(), 1)
        od = ods[0]
        self.assertEqual(od.source_url, 'http://example.org/foo')
        self.assertEqual(od.post.extra.slug, '65808')
