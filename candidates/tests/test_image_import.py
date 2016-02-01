from __future__ import unicode_literals

import hashlib
from os.path import dirname, join

from django.contrib.contenttypes.models import ContentType
from django.test import TestCase

from candidates.models import ImageExtra

from . import factories
from .auth import TestUserMixin


def get_file_md5sum(filename):
    with open(filename, 'rb') as f:
        return hashlib.md5(f.read()).hexdigest()


class TestImageImport(TestUserMixin, TestCase):

    def setUp(self):
        self.labour_extra = factories.PartyExtraFactory.create(
            slug='party:53',
            base__name='Labour Party',
        )
        self.org_ct = ContentType.objects.get_for_model(self.labour_extra)
        self.image_filename = join(
            dirname(__file__), '..', '..', 'moderation_queue', 'tests',
            'media', 'pilot.jpg'
        )

    def test_import_new_image(self):
        md5sum = get_file_md5sum(self.image_filename)
        self.assertEqual(0, self.labour_extra.images.count())
        ImageExtra.objects.update_or_create_from_file(
            self.image_filename, 'images/imported.jpg',
            md5sum=md5sum,
            defaults={
                'copyright': 'example-license',
                'uploading_user': self.user,
                'user_notes': "Here's an image...",
                'base__content_object': self.labour_extra,
                'base__is_primary': True,
                'base__source': "Found on the candidate's Flickr feed",
            }
        )
        self.assertEqual(1, self.labour_extra.images.count())
        # This refetches the object from the database so we don't get
        # ORM-cached data:
        updated_labour = self.labour_extra.images.first()
        updated_labour_extra = updated_labour.extra
        self.assertEqual(updated_labour_extra.copyright, 'example-license')
        self.assertEqual(updated_labour_extra.uploading_user, self.user)
        self.assertEqual(updated_labour_extra.user_notes, "Here's an image...")
        self.assertEqual(updated_labour.source, "Found on the candidate's Flickr feed")
        self.assertTrue(updated_labour.is_primary)

    def test_update_imported_image(self):
        md5sum = get_file_md5sum(self.image_filename)
        self.assertEqual(0, self.labour_extra.images.count())
        ImageExtra.objects.update_or_create_from_file(
            self.image_filename, 'images/imported.jpg',
            md5sum=md5sum,
            defaults={
                'copyright': 'example-license',
                'uploading_user': self.user,
                'user_notes': "Here's an image...",
                'base__content_object': self.labour_extra,
                'base__is_primary': True,
                'base__source': 'Found on the candidates Flickr feed',
            }
        )
        self.assertEqual(1, self.labour_extra.images.count())
        # Now try to update that image:
        ImageExtra.objects.update_or_create_from_file(
            self.image_filename, 'images/imported.jpg',
            md5sum=md5sum,
            defaults={
                'copyright': 'another-license',
                'uploading_user': self.user_who_can_merge,
                'user_notes': "The classic image...",
                'base__content_object': self.labour_extra,
                'base__is_primary': True,
                'base__source': 'The same image from the Flickr feed',
            }
        )
        self.assertEqual(1, self.labour_extra.images.count())
        # This refetches the object from the database so we don't get
        # ORM-cached data:
        updated_labour = self.labour_extra.images.first()
        updated_labour_extra = updated_labour.extra
        self.assertEqual(updated_labour_extra.copyright, 'another-license')
        self.assertEqual(updated_labour_extra.uploading_user, self.user_who_can_merge)
        self.assertEqual(updated_labour_extra.user_notes, "The classic image...")
        self.assertEqual(updated_labour.source, "The same image from the Flickr feed")
        self.assertTrue(updated_labour.is_primary)
