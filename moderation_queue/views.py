import os
import re
import requests
from tempfile import NamedTemporaryFile

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.core.mail import send_mail
from django.core.urlresolvers import reverse
from django.http import HttpResponseRedirect
from django.shortcuts import render, get_object_or_404
from django.template.loader import render_to_string
from django.utils.http import urlquote
from django.views.generic import ListView, TemplateView

from PIL import Image

from braces.views import StaffuserRequiredMixin

from candidates.management.images import get_file_md5sum
from candidates.update import PersonParseMixin, PersonUpdateMixin

from .forms import UploadPersonPhotoForm, PhotoReviewForm
from .models import QueuedImage

from candidates.popit import create_popit_api_object
from candidates.models import PopItPerson, LoggedAction
from candidates.views.version_data import get_client_ip, get_change_metadata


PILLOW_FORMAT_MIME_TYPES = {
    'JPEG': 'image/jpeg',
    'PNG': 'image/png',
    'GIF': 'image/gif',
}


@login_required
def upload_photo(request, popit_person_id):
    if request.method == 'POST':
        form = UploadPersonPhotoForm(request.POST, request.FILES)
        if form.is_valid():
            # Make sure that we save the user that made the upload
            queued_image = form.save(commit=False)
            queued_image.user = request.user
            queued_image.save()
            # Record that action:
            LoggedAction.objects.create(
                user=request.user,
                action_type='photo-upload',
                ip_address=get_client_ip(request),
                popit_person_new_version='',
                popit_person_id=popit_person_id,
                source=form.cleaned_data['justification_for_use'],
            )
            return HttpResponseRedirect(reverse(
                'photo-upload-success',
                kwargs={
                    'popit_person_id': form.cleaned_data['popit_person_id']
                }
            ))
    else:
        form = UploadPersonPhotoForm(
            initial={
                'popit_person_id': popit_person_id
            }
        )
    api = create_popit_api_object()
    return render(
        request,
        'moderation_queue/photo-upload-new.html',
        {'form': form,
         'person': PopItPerson.create_from_popit(api, popit_person_id)}
    )


class PhotoUploadSuccess(PersonParseMixin, TemplateView):
    template_name = 'moderation_queue/photo-upload-success.html'

    def get_context_data(self, **kwargs):
        context = super(PhotoUploadSuccess, self).get_context_data(**kwargs)
        context['person'], _ = self.get_person(kwargs['popit_person_id'])
        return context


class PhotoReviewList(StaffuserRequiredMixin, ListView):
    template_name = 'moderation_queue/photo-review-list.html'

    def get_queryset(self):
        return QueuedImage.objects. \
            filter(decision='undecided'). \
            order_by('created')


def tidy_party_name(name):
    """If a party name contains an initialism in brackets, use that instead

    >>> tidy_party_name('Hello World Party (HWP)')
    'HWP'
    >>> tidy_party_name('Hello World Party')
    'Hello World Party'
    """
    m = re.search(r'\(([A-Z]+)\)', name)
    if m:
        return m.group(1)
    return name


class PhotoReview(StaffuserRequiredMixin, PersonParseMixin, PersonUpdateMixin, TemplateView):
    """The class-based view for approving or rejecting a particular photo"""

    template_name = 'moderation_queue/photo-review.html'
    http_method_names = ['get', 'post']

    def get_google_image_search_url(self, person, person_extra):
        image_search_query = '"{name}" "{party}"'.format(
            name=person['name'],
            party=tidy_party_name(person_extra['last_party']['name'])
        )
        cons_2015 = person['standing_in'].get('2015')
        if cons_2015:
            image_search_query += ' "{0}"'.format(cons_2015['name'])
        return u'https://www.google.co.uk/search?tbm=isch&q={0}'.format(
            urlquote(image_search_query)
        )

    def get_context_data(self, **kwargs):
        context = super(PhotoReview, self).get_context_data(**kwargs)
        self.queued_image = get_object_or_404(
            QueuedImage,
            pk=kwargs['queued_image_id']
        )
        context['queued_image'] = self.queued_image
        context['person'], context['person_extra'] = \
            self.get_person(self.queued_image.popit_person_id)
        context['form'] = PhotoReviewForm(
            initial = {
                'queued_image_id': self.queued_image.id,
                'x_min': 0,
                'x_max': self.queued_image.image.width - 1,
                'y_min': 0,
                'y_max': self.queued_image.image.height - 1,
                'decision': self.queued_image.decision,
                'moderator_why_allowed': self.queued_image.why_allowed,
            }
        )
        context['why_allowed'] = self.queued_image.why_allowed
        context['moderator_why_allowed'] = self.queued_image.why_allowed
        context['justification_for_use'] = self.queued_image.justification_for_use
        context['google_image_search_url'] = self.get_google_image_search_url(
            context['person'], context['person_extra']
        )
        return context

    def send_mail(self, subject, message):
        return send_mail(
            subject,
            message,
            settings.DEFAULT_FROM_EMAIL,
            [self.queued_image.user.email],
            fail_silently=False,
        )

    def crop_and_upload_image_to_popit(self, image_filename, crop_bounds, moderator_why_allowed):
        original = Image.open(image_filename)
        cropped = original.crop(crop_bounds)
        ntf = NamedTemporaryFile(delete=False)
        cropped.save(ntf.name, 'PNG')
        # Upload the image to PopIt...
        image_upload_url = '{base}persons/{person_id}/image'.format(
            base=self.get_base_url(),
            person_id=self.queued_image.popit_person_id
        )
        data = {
            'md5sum': get_file_md5sum(ntf.name),
            'user_why_allowed': self.queued_image.why_allowed,
            'user_justification_for_use': self.queued_image.justification_for_use,
            'moderator_why_allowed': moderator_why_allowed,
            'mime_type': PILLOW_FORMAT_MIME_TYPES[original.format],
            'notes': 'Approved from photo moderation queue',
            'uploaded_by_user': self.queued_image.user.username,
        }
        with open(ntf.name) as f:
            requests.post(
                image_upload_url,
                data=data,
                files={'image': f.read()},
                headers={'APIKey': self.api.api_key}
            )
        # Remove the cropped temporary image file:
        os.remove(ntf.name)

    def form_valid(self, form):
        decision = form.cleaned_data['decision']
        if decision == 'approved':
            # Crop the image...
            self.crop_and_upload_image_to_popit(
                self.queued_image.image.path,
                [form.cleaned_data[e] for e in
                 ('x_min', 'y_min', 'x_max', 'y_max')],
                form.cleaned_data['moderator_why_allowed']
            )
            self.queued_image.decision = 'approved'
            self.queued_image.save()
            # Now create a new version in PopIt:
            person_data, _ = self.get_person(
                self.queued_image.popit_person_id
            )
            previous_versions = person_data.pop('versions')
            update_message = (u'Approved a photo upload from ' +
                u'{uploading_user} who provided the message: ' +
                u'"{message}"').format(
                uploading_user=self.queued_image.user.username,
                message=self.queued_image.justification_for_use,
            )
            change_metadata = get_change_metadata(
                self.request,
                update_message
            )
            self.update_person(
                person_data,
                change_metadata,
                previous_versions,
            )
            LoggedAction.objects.create(
                user=self.request.user,
                action_type='photo-approve',
                ip_address=get_client_ip(self.request),
                popit_person_new_version=change_metadata['version_id'],
                popit_person_id=self.queued_image.popit_person_id,
                source=update_message,
            )
            candidate_path = reverse(
                'person-view',
                kwargs={'person_id': self.queued_image.popit_person_id}
            )
            self.send_mail(
                'YourNextMP image upload approved',
                render_to_string(
                    'moderation_queue/photo_approved_email.txt',
                    {'candidate_page_url':
                     self.request.build_absolute_uri(candidate_path)}
                ),
            )
        elif decision == 'rejected':
            self.queued_image.decision = 'rejected'
            self.queued_image.save()
            update_message = u'Rejected a photo upload from ' + \
                u'{uploading_user}'.format(
                uploading_user=self.queued_image.user.username,
            )
            LoggedAction.objects.create(
                user=self.request.user,
                action_type='photo-reject',
                ip_address=get_client_ip(self.request),
                popit_person_new_version='',
                popit_person_id=self.queued_image.popit_person_id,
                source=update_message,
            )
            self.send_mail(
                'YourNextMP image moderation results',
                render_to_string(
                    'moderation_queue/photo_rejected_email.txt',
                    {'reason': form.cleaned_data['rejection_reason']}
                ),
            )
        elif decision == 'undecided':
            # If it's left as undecided, just redirect back to the
            # photo review queue...
            pass
        else:
            raise Exception("BUG: unexpected decision {0}".format(decision))
        return HttpResponseRedirect(reverse('photo-review-list'))

    def form_invalid(self, form):
        return self.render_to_response(
            self.get_context_data(
                queued_image_id=self.queued_image.id,
                form=form
            )
        )

    def post(self, request, *args, **kwargs):
        self.queued_image = QueuedImage.objects.get(
            pk=kwargs['queued_image_id']
        )
        form = PhotoReviewForm(data=self.request.POST)
        if form.is_valid():
            return self.form_valid(form)
        else:
            return self.form_invalid(form)
