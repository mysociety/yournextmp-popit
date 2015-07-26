from django.http import Http404
from django.views.generic import TemplateView
from django.utils.translation import ugettext as _

import requests

from cached_counts.models import CachedCount
from elections.mixins import ElectionMixin

from ..popit import PopItApiMixin, popit_unwrap_pagination, get_search_url
from ..election_specific import PARTY_DATA, AREA_POST_DATA


class PartyListView(ElectionMixin, PopItApiMixin, TemplateView):
    template_name = 'candidates/party-list.html'

    def get_context_data(self, **kwargs):
        context = super(PartyListView, self).get_context_data(**kwargs)
        party_ids_with_any_candidates = set(
            CachedCount.objects.filter(count_type='party', count__gt=0). \
                values_list('object_id', flat=True)
        )
        parties = []
        for party in popit_unwrap_pagination(
            self.api.organizations,
            embed='',
            per_page=100
        ):
            if party.get('classification') != 'Party':
                continue
            if party['id'] in party_ids_with_any_candidates:
                parties.append((party['name'], party['id']))
        parties.sort()
        context['parties'] = parties
        return context


def get_post_group_stats(posts):
    total = 0
    candidates = 0
    for t in posts:
        total += 1
        if t[2]:
            candidates += 1
    proportion = candidates / float(total)
    return {
        'proportion': proportion,
        'total': total,
        'candidates': candidates,
        'missing': total - candidates,
        'show_all': proportion > 0.3,
    }


class PartyDetailView(ElectionMixin, PopItApiMixin, TemplateView):
    template_name = 'candidates/party.html'

    def get_context_data(self, **kwargs):
        context = super(PartyDetailView, self).get_context_data(**kwargs)
        party_id = kwargs['organization_id']
        party_name = PARTY_DATA.party_id_to_name.get(party_id)
        if not party_name:
            raise Http404(_("Party not found"))
        party = self.api.organizations(party_id).get(embed='')['result']

        # Make the party emblems conveniently available in the context too:
        context['emblems'] = [
            (i.get('notes', ''), i['proxy_url'] + '/240/0')
            for i in party.get('images', [])
        ]
        by_post_group = {
            pg: {} for pg in AREA_POST_DATA.ALL_POSSIBLE_POST_GROUPS
        }
        url = get_search_url(
            'persons',
            'party_memberships.{0}.id:"{1}"'.format(
                self.election,
                party_id,
            ),
            per_page=100
        )
        while url:
            page_result = requests.get(url).json()
            next_url = page_result.get('next_url')
            url = next_url if next_url else None
            for person in page_result['result']:
                standing_in = person.get('standing_in')
                if not (standing_in and standing_in.get(self.election)):
                    continue
                post_id = standing_in[self.election].get('post_id')
                post_name = standing_in[self.election].get('name')
                post_group = AREA_POST_DATA.post_id_to_post_group(
                    kwargs['election'], post_id
                )
                by_post_group[post_group][post_id] = {
                    'person_id': person['id'],
                    'person_name': person['name'],
                    'post_id': post_id,
                    'constituency_name': post_name,
                }
        context['party'] = party
        context['party_name'] = party_name
        relevant_post_groups = AREA_POST_DATA.party_to_possible_post_groups(party)
        candidates_by_post_group = {}
        for post_group in relevant_post_groups:
            candidates_by_post_group[post_group] = None
            if by_post_group[post_group]:
                posts = [
                    (c[0], c[1], by_post_group[post_group].get(
                        AREA_POST_DATA.get_post_id(self.election, mapit_type, c[0])
                    ))
                    for mapit_type in self.election_data['mapit_types']
                    for c in AREA_POST_DATA.area_ids_and_names_by_post_group[
                        (mapit_type, self.election_data['mapit_generation'])
                    ][post_group]
                ]
                candidates_by_post_group[post_group] = {
                    'constituencies': posts,
                    'stats': get_post_group_stats(posts),
                }
        context['candidates_by_post_group'] = sorted(
            candidates_by_post_group.items(),
            key=lambda k: k[0]
        )
        return context
