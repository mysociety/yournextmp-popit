from django.conf.urls import patterns

from .feeds import (
    BasicResultEventsFeed,
    ResultEventsFeed,
)


urlpatterns = patterns('',
    (r'^all\.atom$', ResultEventsFeed()),
    (r'^all-basic\.atom$', BasicResultEventsFeed()),
)
