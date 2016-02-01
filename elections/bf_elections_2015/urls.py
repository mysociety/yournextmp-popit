from __future__ import unicode_literals

from django.conf.urls import url

from . import views

urlpatterns = [
    url(
        r'^$',
        views.BurkinaFasoAddressFinder.as_view(),
        name='lookup-address',
    ),
]
