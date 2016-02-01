from __future__ import unicode_literals

from django.conf.urls import patterns, url

from .views import IncompleteFieldView, TaskHomeView

urlpatterns = patterns('',
    url(r'^$', TaskHomeView.as_view(), name='tasks_home'),
    url(
        r'(?P<field>[a-z_\-\.]+)/',
        IncompleteFieldView.as_view(),
        name='incomplete_view',
    ),
)
