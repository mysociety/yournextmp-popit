import json

from django.conf import settings
from django.http import HttpResponse

from django.views.generic import ListView, TemplateView

from elections.mixins import ElectionMixin

from .models import CachedCount


def get_count(all_counts, **kwargs):
    matching_counts = [
        cc['count'] for cc in
        all_counts
        if all(cc[k] == v for k, v in kwargs.items())
    ]
    if len(matching_counts) == 0:
        return None
    if len(matching_counts) > 1:
        raise Exception, "Multiple counts found matching {0}". \
            format(kwargs)
    return matching_counts[0]

def get_prior_election_data(all_counts, current_election_id, prior_id, prior_data):
    result = {
        count_type: get_count(
            all_counts,
            election=current_election_id,
            object_id=prior_id,
            count_type=count_type
        )
        for count_type in (
                'new_candidates',
                'standing_again',
                'standing_again_different_party',
                'standing_again_same_party',
        )
    }
    result.update({
        'name': prior_data['name'],
        'total': get_count(
            all_counts,
            election=prior_id,
            count_type='total',
        )
    })
    result['percentage'] = \
        100 * float(get_count(
            all_counts,
            election=current_election_id,
            count_type='total'
        )) / result['total']
    return result


def get_counts():

    all_elections = {
        'current':
        [{'id': t[0], 'name': t[1]['name']}
         for t in settings.ELECTIONS_CURRENT],
        'past':
        [{'id': t[0], 'name': t[1]['name']}
         for t in settings.ELECTIONS_BY_DATE
         if not t[1]['current']],
    }

    counts = CachedCount.objects.values()

    for era, election_list in all_elections.items():
        for election_dict in election_list:
            election = election_dict['id']
            election_dict['total'] = get_count(
                counts, election=election, count_type='total'
            )
            if era == 'current':
                election_dict['prior_elections'] = [
                    get_prior_election_data(
                        counts, election, prior_election_id, prior_election_data
                    )
                    for prior_election_id, prior_election_data
                    in settings.ELECTIONS_BY_DATE
                    if not prior_election_data['current']
                ]

    return all_elections


class ReportsHomeView(TemplateView):
    template_name = "reports.html"

    def get_context_data(self, **kwargs):
        context = super(ReportsHomeView, self).get_context_data(**kwargs)
        context['all_elections'] = get_counts()
        return context

    def get(self, *args, **kwargs):
        if self.request.GET.get('format') == "json":
            return HttpResponse(
                json.dumps(get_counts()),
                content_type="application/json"
            )
        return super(ReportsHomeView, self).get(*args, **kwargs)


class PartyCountsView(ElectionMixin, ListView):
    template_name = "party_counts.html"

    def get_queryset(self):
        return CachedCount.objects.filter(
            election=self.kwargs['election'],
            count_type='party',
        )


class ConstituencyCountsView(ElectionMixin, ListView):
    template_name = "constituency_counts.html"

    def get_queryset(self):
        return CachedCount.objects.filter(
            election=self.kwargs['election'],
            count_type='post',
        )


class AttentionNeededView(ListView):
    template_name = "attention_needed.html"

    def get_queryset(self):
        return CachedCount.get_attention_needed_queryset()
