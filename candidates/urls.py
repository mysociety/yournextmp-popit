from django.conf import settings
from django.conf.urls import patterns, include, url
from django.contrib import admin
from django.views.generic import TemplateView

import candidates.views as views

from .feeds import RecentChangesFeed

urlpatterns = \
    patterns('',
        (r'^', include(settings.ELECTION_APP_FULLY_QUALIFIED + '.urls')),
    )

patterns_to_format = [
    {
        'pattern': r'^$',
        'view': views.AddressFinderView.as_view(),
        'name': 'lookup-address',
    },
    {
        'pattern': r'^posts$',
        'view': views.PostListView.as_view(),
        'name': 'posts',
    },
    {
        'pattern': r'^election/{election}/constituencies$',
        'view': views.ConstituencyListView.as_view(),
        'name': 'constituencies'
    },
    {
        'pattern': r'^election/{election}/constituencies/unlocked$',
        'view': views.ConstituenciesUnlockedListView.as_view(),
        'name': 'constituencies-unlocked'
    },
    {
        'pattern': r'^election/{election}/constituencies/declared$',
        'view': views.ConstituenciesDeclaredListView.as_view(),
        'name': 'constituencies-declared'
    },
    {
        'pattern': r'^election/{election}/post/{post}/record-winner$',
        'view': views.ConstituencyRecordWinnerView.as_view(),
        'name': 'record-winner'
    },
    {
        'pattern': r'^election/{election}/post/{post}/retract-winner$',
        'view': views.ConstituencyRetractWinnerView.as_view(),
        'name': 'retract-winner'
    },
    {
        'pattern': r'^election/{election}/post/invalidate$',
        'view': views.InvalidatePostView.as_view(),
        'name': 'post-cache-invalidate'
    },
    {
        'pattern': r'^election/{election}/post/{post}/(?P<ignored_slug>.*).csv$',
        'view': views.ConstituencyDetailCSVView.as_view(),
        'name': 'constituency_csv'
    },
    {
        'pattern': r'^election/{election}/post/{post}/(?P<ignored_slug>.*)$',
        'view': views.ConstituencyDetailView.as_view(),
        'name': 'constituency'
    },
    {
        'pattern': r'^election/{election}/party-list/{post}/(?P<organization_id>[a-z-]+(:[-\d]+)?)$',
        'view': views.OrderedPartyListView.as_view(),
        'name': 'party-for-post'
    },
    {
        'pattern': r'^election/{election}/post/lock$',
        'view': views.ConstituencyLockView.as_view(),
        'name': 'constituency-lock'
    },
    {
        'pattern': r'^election/{election}/candidacy$',
        'view': views.CandidacyView.as_view(),
        'name': 'candidacy-create'
    },
    {
        'pattern': r'^election/{election}/candidacy/delete$',
        'view': views.CandidacyDeleteView.as_view(),
        'name': 'candidacy-delete'
    },
    {
        'pattern': r'^election/{election}/person/create/$',
        'view': views.NewPersonView.as_view(),
        'name': 'person-create'
    },
    {
        'pattern': r'^person/(?P<person_id>\d+)/update$',
        'view': views.UpdatePersonView.as_view(),
        'name': 'person-update'
    },
    {
        'pattern': r'^update-disallowed$',
        'view': TemplateView.as_view(template_name="candidates/update-disallowed.html"),
        'name': 'update-disallowed'
    },
    {
        'pattern': r'^all-edits-disallowed$',
        'view': TemplateView.as_view(template_name="candidates/all-edits-disallowed.html"),
        'name': 'all-edits-disallowed'
    },
    {
        'pattern': r'^person/(?P<person_id>\d+)/revert$',
        'view': views.RevertPersonView.as_view(),
        'name': 'person-revert'
    },
    {
        'pattern': r'^person/(?P<person_id>\d+)/merge$',
        'view': views.MergePeopleView.as_view(),
        'name': 'person-merge'
    },
    {
        'pattern': r'^person/(?P<person_id>\d+)(?:/(?P<ignored_slug>.*))?$',
        'view': views.PersonView.as_view(),
        'name': 'person-view'
    },
    {
        'pattern': r'^areas/(?P<type_and_area_ids>.*?)(?:/(?P<ignored_slug>.*))?$',
        'view': views.AreasView.as_view(),
        'name': 'areas-view',
    },
    {
        'pattern': r'^areas-of-type/(?P<mapit_type>.*?)(?:/(?P<ignored_slug>.*))?$',
        'view': views.AreasOfTypeView.as_view(),
        'name': 'areas-of-type-view',
    },
    {
        'pattern': r'^election/{election}/party/(?P<organization_id>[a-z-]+(:[-\d]+)?)/(?P<ignored_slug>.*)$',
        'view': views.PartyDetailView.as_view(),
        'name': 'party'
    },
    {
        'pattern': r'^election/{election}/parties/?$',
        'view': views.PartyListView.as_view(),
        'name': 'party-list'
    },
    {
        'pattern': r'^recent-changes$',
        'view': views.RecentChangesView.as_view(),
        'name': 'recent-changes'
    },
    {
        'pattern': r'^leaderboard$',
        'view': views.LeaderboardView.as_view(),
        'name': 'leaderboard'
    },
    {
        'pattern': r'^leaderboard/contributions.csv',
        'view': views.UserContributions.as_view(),
        'name': 'user-contributions'
    },
    {
        'pattern': r'^feeds/changes.xml',
        'view': RecentChangesFeed(),
        'name': 'changes_feed'
    },
    {
        'pattern': r'^help/api',
        'view': views.HelpApiView.as_view(),
        'name': 'help-api'
    },
    {
        'pattern': r'^help/about',
        'view': views.HelpAboutView.as_view(),
        'name': 'help-about'
    },
    {
        'pattern': r'^help/privacy',
        'view': TemplateView.as_view(template_name="candidates/privacy.html"),
        'name': 'help-privacy'
    },
    {
        'pattern': r'^copyright-question',
        'view': views.AskForCopyrightAssigment.as_view(),
        'name': 'ask-for-copyright-assignment'
    },
    {
        'pattern': r'^person/invalidate$',
        'view': views.InvalidatePersonView.as_view(),
        'name': 'person-cache-invalidate'
    },
]

urlpatterns += [
    url(
        p['pattern'].format(
            election=settings.ELECTION_RE,
            post=r'(?P<post_id>[-\w]+)',
        ),
        p['view'],
        name=p['name'],
    )
    for p in patterns_to_format
]

urlpatterns += [
    url(r'^numbers/', include('cached_counts.urls')),
    url(r'^moderation/', include('moderation_queue.urls')),
    url(r'^admin/', include(admin.site.urls)),
]
