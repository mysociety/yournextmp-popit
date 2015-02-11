from django.core.urlresolvers import reverse
from django.http import HttpResponseRedirect
from django.shortcuts import render
from django.views.generic import TemplateView

from .forms import UploadPersonPhotoForm

def upload_photo(request):
    if request.method == 'POST':
        form = UploadPersonPhotoForm(request.POST, request.FILES)
        if form.is_valid():
            # Make sure that we save the user that made the upload
            queued_image = form.save(commit=False)
            queued_image.user = request.user
            queued_image.save()
            return HttpResponseRedirect(reverse(
                'photo-upload-success',
                kwargs={
                    'popit_person_id': form.cleaned_data['popit_person_id']
                }
            ))
    else:
        form = UploadPersonPhotoForm()
    return render(
        request,
        'moderation_queue/photo-upload-new.html',
        {'form': form}
    )


class PhotoUploadSuccess(TemplateView):
    template_name = 'moderation_queue/photo-upload-success.html'
