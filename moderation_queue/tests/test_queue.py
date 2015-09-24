# -*- coding: utf-8 -*-

from os.path import join, realpath, dirname
import re
from urlparse import urlsplit

from django.contrib.auth.models import User, Group
from django.contrib.sites.models import Site
from django.core.urlresolvers import reverse
from django.test.utils import override_settings

from PIL import Image
import StringIO
from django_webtest import WebTest
from mock import patch

from ..models import QueuedImage, PHOTO_REVIEWERS_GROUP_NAME
from candidates.models import LoggedAction
from candidates.tests.fake_popit import FakePersonCollection

TEST_MEDIA_ROOT=realpath(join(dirname(__file__), 'media'))

def get_image_type_and_dimensions(image_data):
    image = Image.open(StringIO.StringIO(image_data))
    return {
        'format': image.format,
        'width': image.size[0],
        'height': image.size[1],
    }

class PhotoReviewTests(WebTest):

    @override_settings(MEDIA_ROOT=TEST_MEDIA_ROOT)
    def setUp(self):
        self.site = Site.objects.create(domain='example.com', name='YNR')
        self.test_upload_user = User.objects.create_user(
            'john',
            'john@example.com',
            'notagoodpassword',
        )
        self.test_upload_user.terms_agreement.assigned_to_dc = True
        self.test_upload_user.terms_agreement.save()
        self.test_reviewer = User.objects.create_superuser(
            'jane',
            'jane@example.com',
            'alsonotagoodpassword',
        )
        self.test_reviewer.terms_agreement.assigned_to_dc = True
        self.test_reviewer.terms_agreement.save()
        self.test_reviewer.groups.add(
            Group.objects.get(name=PHOTO_REVIEWERS_GROUP_NAME)
        )
        self.q1 = QueuedImage.objects.create(
            why_allowed='public-domain',
            justification_for_use="It's their Twitter avatar",
            decision='undecided',
            image='pilot.jpg',
            popit_person_id='2009',
            user=self.test_upload_user
        )
        self.q2 = QueuedImage.objects.create(
            why_allowed='copyright-assigned',
            justification_for_use="I took this last week",
            decision='approved',
            image='pilot.jpg',
            popit_person_id='2007',
            user=self.test_upload_user
        )
        self.q3 = QueuedImage.objects.create(
            why_allowed='other',
            justification_for_use="I found it somewhere",
            decision='rejected',
            image='pilot.jpg',
            popit_person_id='2007',
            user=self.test_reviewer
        )

    def tearDown(self):
        self.q1.delete()
        self.q2.delete()
        self.q3.delete()
        self.test_upload_user.delete()
        self.test_reviewer.delete()
        self.site.delete()

    @override_settings(MEDIA_ROOT=TEST_MEDIA_ROOT)
    def test_photo_review_queue_view_not_logged_in(self):
        queue_url = reverse('photo-review-list')
        response = self.app.get(queue_url)
        self.assertEqual(response.status_code, 302)
        split_location = urlsplit(response.location)
        self.assertEqual('/accounts/login/', split_location.path)
        self.assertEqual('next=/moderation/photo/review', split_location.query)

    @override_settings(MEDIA_ROOT=TEST_MEDIA_ROOT)
    def test_photo_review_queue_view_logged_in_unprivileged(self):
        queue_url = reverse('photo-review-list')
        response = self.app.get(
            queue_url,
            user=self.test_upload_user,
            expect_errors=True,
        )
        self.assertEqual(response.status_code, 403)

    @override_settings(MEDIA_ROOT=TEST_MEDIA_ROOT)
    def test_photo_review_queue_view_logged_in_privileged(self):
        queue_url = reverse('photo-review-list')
        response = self.app.get(queue_url, user=self.test_reviewer)
        self.assertEqual(response.status_code, 200)
        queue_table = response.html.find('table')
        photo_rows = queue_table.find_all('tr')
        self.assertEqual(2, len(photo_rows))
        cells = photo_rows[1].find_all('td')
        self.assertEqual(cells[1].text, 'john')
        self.assertEqual(cells[2].text, '2009')
        a = cells[3].find('a')
        link_text = re.sub(r'\s+', ' ', a.text).strip()
        link_url = a['href']
        self.assertEqual(link_text, 'Review')
        self.assertEqual(link_url, '/moderation/photo/review/{0}'.format(self.q1.id))

    @patch('candidates.popit.PopIt')
    @override_settings(MEDIA_ROOT=TEST_MEDIA_ROOT)
    def test_photo_review_view_unprivileged(self, mock_popit):
        mock_popit.return_value.persons = FakePersonCollection
        review_url = reverse(
            'photo-review',
            kwargs={'queued_image_id': self.q1.id}
        )
        response = self.app.get(
            review_url,
            user=self.test_upload_user,
            expect_errors=True
        )
        self.assertEqual(response.status_code, 403)

    @patch('candidates.popit.PopIt')
    @override_settings(MEDIA_ROOT=TEST_MEDIA_ROOT)
    def test_photo_review_view_privileged(self, mock_popit):
        mock_popit.return_value.persons = FakePersonCollection
        review_url = reverse(
            'photo-review',
            kwargs={'queued_image_id': self.q1.id}
        )
        response = self.app.get(review_url, user=self.test_reviewer)
        self.assertEqual(response.status_code, 200)
        # For the moment this is just a smoke test...

    @patch('moderation_queue.views.send_mail')
    @patch('moderation_queue.views.requests.post')
    @patch('candidates.models.popit.invalidate_person')
    @patch('candidates.models.popit.invalidate_posts')
    @patch.object(FakePersonCollection, 'put')
    @patch('candidates.popit.PopIt')
    @override_settings(MEDIA_ROOT=TEST_MEDIA_ROOT)
    @override_settings(DEFAULT_FROM_EMAIL='admins@example.com')
    def test_photo_review_upload_approved_privileged(
            self,
            mock_popit,
            mocked_person_put,
            mock_invalidate_posts,
            mock_invalidate_person,
            mock_requests_post,
            mock_send_mail
    ):
        with self.settings(SITE_ID=self.site.id):
            mock_popit.return_value.persons = FakePersonCollection
            review_url = reverse(
                'photo-review',
                kwargs={'queued_image_id': self.q1.id}
            )
            review_page_response = self.app.get(
                review_url,
                user=self.test_reviewer
            )
            form = review_page_response.forms['photo-review-form']
            form['decision'] = 'approved'
            form['moderator_why_allowed'] = 'profile-photo'
            response = form.submit(user=self.test_reviewer)
            # FIXME: check that mocked_person_put got the right calls
            self.assertEqual(response.status_code, 302)
            split_location = urlsplit(response.location)
            self.assertEqual('/moderation/photo/review', split_location.path)

            mock_send_mail.assert_called_once_with(
                'YNR image upload approved',
                u"Thank-you for submitting a photo to YNR; that's been\nuploaded now for the candidate page here:\n\n  http://localhost:80/person/2009/tessa-jowell\n\nMany thanks,\nThe YNR volunteers\n",
                'admins@example.com',
                [u'john@example.com'],
                fail_silently=False
            )

            self.assertEqual(mock_requests_post.call_count, 1)
            post_call_args, post_call_kwargs = mock_requests_post.call_args_list[0]
            self.assertEqual(1, len(post_call_args))
            self.assertTrue(
                re.search(r'/persons/2009/image$', post_call_args[0])
            )
            self.assertEqual(
                set(post_call_kwargs.keys()),
                set(['files', 'headers', 'data']),
            )
            self.assertIn('APIKey', post_call_kwargs['headers'])
            posted_image_data = post_call_kwargs['files']['image']
            self.assertEqual(
                get_image_type_and_dimensions(posted_image_data),
                {'format': 'PNG', 'width': 427, 'height': 639},
            )
            del post_call_kwargs['data']['md5sum']
            self.assertEqual(
                post_call_kwargs['data'],
                {'user_justification_for_use':
                 u"It's their Twitter avatar",
                 'notes': 'Approved from photo moderation queue',
                 'user_why_allowed': u'public-domain',
                 'moderator_why_allowed': u'profile-photo',
                 'uploaded_by_user': u'john',
                 'index': 'first',
                 'mime_type': 'image/png',
                 'created': None}
            )
            las = LoggedAction.objects.all()
            self.assertEqual(1, len(las))
            la = las[0]
            self.assertEqual(la.user.username, 'jane')
            self.assertEqual(la.action_type, 'photo-approve')
            self.assertEqual(la.popit_person_id, '2009')

            mock_invalidate_person.assert_called_with('2009')
            mock_invalidate_posts.assert_called_with(set(['65808']))

            self.assertEqual(QueuedImage.objects.get(pk=self.q1.id).decision, 'approved')

    @patch('moderation_queue.views.send_mail')
    @patch('moderation_queue.views.requests.post')
    @patch('candidates.popit.PopIt')
    @override_settings(MEDIA_ROOT=TEST_MEDIA_ROOT)
    @override_settings(DEFAULT_FROM_EMAIL='admins@example.com')
    @override_settings(SUPPORT_EMAIL='support@example.com')
    def test_photo_review_upload_rejected_privileged(
            self,
            mock_popit,
            mock_requests_post,
            mock_send_mail
    ):
        with self.settings(SITE_ID=self.site.id):
            mock_popit.return_value.persons = FakePersonCollection
            review_url = reverse(
                'photo-review',
                kwargs={'queued_image_id': self.q1.id}
            )
            review_page_response = self.app.get(
                review_url,
                user=self.test_reviewer
            )
            form = review_page_response.forms['photo-review-form']
            form['decision'] = 'rejected'
            form['rejection_reason'] = u'There\'s no clear source or copyright statement'
            response = form.submit(user=self.test_reviewer)
            self.assertEqual(response.status_code, 302)
            split_location = urlsplit(response.location)
            self.assertEqual('/moderation/photo/review', split_location.path)

            las = LoggedAction.objects.all()
            self.assertEqual(1, len(las))
            la = las[0]
            self.assertEqual(la.user.username, 'jane')
            self.assertEqual(la.action_type, 'photo-reject')
            self.assertEqual(la.popit_person_id, '2009')
            self.assertEqual(la.source, 'Rejected a photo upload from john')

            mock_send_mail.assert_called_once_with(
                'YNR image moderation results',
                u"Thank-you for uploading a photo of Tessa Jowell\nto YNR, but unfortunately we can't use that image because:\n\n  There\'s no clear source or copyright statement\n\nYou can just reply to this email if you want to discuss that\nfurther, or you can try uploading a photo with a different reason\nor justification for its use using this link:\n\n  http://localhost:80/moderation/photo/upload/2009\n\nMany thanks,\nThe YNR volunteers\n\n-- \nFor administrators' use: http://localhost:80/moderation/photo/review/1\n",
                'admins@example.com',
                [u'john@example.com', 'support@example.com'],
                fail_silently=False
            )

            self.assertEqual(mock_requests_post.call_count, 0)

            self.assertEqual(QueuedImage.objects.get(pk=self.q1.id).decision, 'rejected')

    @patch('moderation_queue.views.send_mail')
    @patch('moderation_queue.views.requests.post')
    @patch('candidates.popit.PopIt')
    @override_settings(MEDIA_ROOT=TEST_MEDIA_ROOT)
    @override_settings(DEFAULT_FROM_EMAIL='admins@example.com')
    def test_photo_review_upload_undecided_privileged(
            self,
            mock_popit,
            mock_requests_post,
            mock_send_mail
    ):
        mock_popit.return_value.persons = FakePersonCollection
        review_url = reverse(
            'photo-review',
            kwargs={'queued_image_id': self.q1.id}
        )
        review_page_response = self.app.get(
            review_url,
            user=self.test_reviewer
        )
        form = review_page_response.forms['photo-review-form']
        form['decision'] = 'undecided'
        form['rejection_reason'] = 'No clear source or copyright statement'
        response = form.submit(user=self.test_reviewer)
        self.assertEqual(response.status_code, 302)
        split_location = urlsplit(response.location)
        self.assertEqual('/moderation/photo/review', split_location.path)

        self.assertEqual(mock_send_mail.call_count, 0)
        self.assertEqual(mock_requests_post.call_count, 0)

        self.assertEqual(QueuedImage.objects.get(pk=self.q1.id).decision, 'undecided')

    @patch('moderation_queue.views.send_mail')
    @patch('moderation_queue.views.requests.post')
    @patch('candidates.popit.PopIt')
    @override_settings(MEDIA_ROOT=TEST_MEDIA_ROOT)
    @override_settings(DEFAULT_FROM_EMAIL='admins@example.com')
    def test_photo_review_upload_ignore_privileged(
            self,
            mock_popit,
            mock_requests_post,
            mock_send_mail
    ):
        mock_popit.return_value.persons = FakePersonCollection
        review_url = reverse(
            'photo-review',
            kwargs={'queued_image_id': self.q1.id}
        )
        review_page_response = self.app.get(
            review_url,
            user=self.test_reviewer
        )
        form = review_page_response.forms['photo-review-form']
        form['decision'] = 'ignore'
        response = form.submit(user=self.test_reviewer)
        self.assertEqual(response.status_code, 302)
        split_location = urlsplit(response.location)
        self.assertEqual('/moderation/photo/review', split_location.path)

        self.assertEqual(mock_send_mail.call_count, 0)
        self.assertEqual(mock_requests_post.call_count, 0)

        self.assertEqual(QueuedImage.objects.get(pk=self.q1.id).decision, 'ignore')

        las = LoggedAction.objects.all()
        self.assertEqual(1, len(las))
        la = las[0]
        self.assertEqual(la.user.username, 'jane')
        self.assertEqual(la.action_type, 'photo-ignore')
        self.assertEqual(la.popit_person_id, '2009')
