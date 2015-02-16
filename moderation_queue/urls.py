from django.conf.urls import patterns, url

from .views import upload_photo, PhotoUploadSuccess

urlpatterns = patterns('',
    url(r'^photo/upload$', upload_photo, name="photo-upload"),
    url(r'^photo/upload/success/(?P<popit_person_id>\d+)$',
        PhotoUploadSuccess.as_view(),
        name="photo-upload-success"),
)
