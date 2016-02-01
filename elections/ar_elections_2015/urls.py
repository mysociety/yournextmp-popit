from __future__ import unicode_literals

from django.conf.urls import url
from django.views.generic import TemplateView

from . import views

urlpatterns = [
    url(
        r'^$',
        views.ArgentineAddressFinder.as_view(),
        name='lookup-address',
    ),
    url(
        r'^help/reutiliza$',
        TemplateView.as_view(template_name='candidates/reuse.html'),
        name='help-reuse',
    ),
]
