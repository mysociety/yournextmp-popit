from datetime import timedelta

from django.contrib.auth.models import User
from django.db.models import Count
from django.utils import timezone

from ..models import LoggedAction
from ..static_data import MapItData


class ContributorsMixin(object):

    def get_leaderboards(self):
        result = []
        for title, since in [
            ('All Time', None),
            ('In the last week', timezone.now() - timedelta(days=7))
        ]:
            interesting_actions=LoggedAction.objects.exclude(
                action_type='set-candidate-not-elected'
            )
            if since:
                qs = interesting_actions.filter(created__gt=since)
            else:
                qs = interesting_actions
            rows = qs.values('user'). \
                annotate(edit_count=Count('user')).order_by('-edit_count')[:25]
            for row in rows:
                row['username'] = User.objects.get(pk=row['user'])
            leaderboard = {
                'title': title,
                'rows': rows,
            }
            result.append(leaderboard)
        return result

    def get_recent_changes_queryset(self):
        return LoggedAction.objects.exclude(action_type='set-candidate-not-elected').order_by('-created')


class CandidacyMixin(object):

    def get_area_from_post_id(self, post_id, mapit_url_key='id'):
        "Get a MapIt area ID from a candidate list organization's PopIt data"

        mapit_data = MapItData.constituencies_2010.get(post_id)
        if mapit_data is None:
            message = "Couldn't find the constituency with Post and MapIt Area ID: '{0}'"
            raise Exception(message.format(post_id))
        url_format = 'http://mapit.mysociety.org/area/{0}'
        return {
            'name': mapit_data['name'],
            'post_id': post_id,
            mapit_url_key: url_format.format(post_id),
        }
