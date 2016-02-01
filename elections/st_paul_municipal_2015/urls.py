from __future__ import unicode_literals

from django.conf import settings
from django.conf.urls import url
from candidates.views.constituencies import ConstituencyDetailView

from . import views

post_ignored_slug_re = r'(?!record-winner$|retract-winner$|.*\.csv$).*'

urlpatterns = [
    url(
        r'^$',
        views.StPaulAddressFinder.as_view(),
        name='lookup-name'
    ),
    url(
        r'^areas/(?P<area_ids>.*?)$',
        views.StPaulAreasView.as_view(),
        name='st-paul-areas-view'
    ),
    url(
        r'^areas-of-type/(?P<area_type>.*?)(?:/(?P<ignored_slug>.*))?$',
        views.StPaulAreasOfTypeView.as_view(),
        name='areas-of-type-view'
    ),
    url(
        r'^election/{election}/post/(?P<post_id>.*)/(?P<ignored_slug>{ignore_pattern})$'.format(
            election=r'(?P<election>[^/]+)',
            ignore_pattern=post_ignored_slug_re,
        ),
        ConstituencyDetailView.as_view(),
        name='constituency'
    ),
]
