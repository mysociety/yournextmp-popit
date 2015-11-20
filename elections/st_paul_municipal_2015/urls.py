from django.conf import settings
from django.conf.urls import url
from candidates.views.constituencies import ConstituencyDetailView, \
    ConstituencyRecordWinnerView, ConstituencyRetractWinnerView

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
        r'^areas/(?P<type_and_area_ids>.*?)(?:/(?P<ignored_slug>.*))?$',
        views.StPaulAreasOfTypeView.as_view(),
        name='st-paul-areas-of-type-view'
    ),
    url(
        r'^election/{election}/post/{post}/record-winner$'.format(
            election=settings.ELECTION_RE,
            post=r'(?P<post_id>.*)',
        ),
        ConstituencyRecordWinnerView.as_view(),
        name='record-winner',
    ),
    url(
        r'^election/{election}/post/{post}/retract-winner$'.format(
            election=settings.ELECTION_RE,
            post=r'(?P<post_id>.*)',
        ),
        ConstituencyRetractWinnerView.as_view(),
        name='retract-winner',
    ),
    url(
        r'^election/{election}/post/(?P<post_id>.*)/(?P<ignored_slug>{ignore_pattern})$'.format(
            election=settings.ELECTION_RE,
            ignore_pattern=post_ignored_slug_re,
        ),
        views.ConstituencyDetailView.as_view(),
        name='constituency'
    ),
]
