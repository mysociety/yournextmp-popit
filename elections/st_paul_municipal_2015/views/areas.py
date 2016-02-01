# -*- coding: utf-8 -*-

from __future__ import unicode_literals

import re

from django.core.urlresolvers import reverse
from django.db.models import Prefetch
from django.http import Http404, HttpResponseRedirect
from django.shortcuts import get_object_or_404
from django.views.generic import TemplateView
from django.utils.text import slugify
from django.utils.translation import ugettext as _

from candidates.models import AreaExtra, MembershipExtra
from candidates.models.auth import get_edits_allowed
from candidates.forms import NewPersonForm
from candidates.views.helpers import split_candidacies, group_candidates_by_party

from elections.models import AreaType, Election


class StPaulAreasView(TemplateView):
    template_name = 'candidates/areas.html'

    def get(self, request, *args, **kwargs):
        try:
            area_ids = kwargs['area_ids']
        except KeyError:
            return HttpResponseRedirect('/')
        self.area_ids = [o for o in area_ids.split(';')]
        view = super(StPaulAreasView, self).get(request, *args, **kwargs)
        return view

    def get_context_data(self, **kwargs):
        context = super(StPaulAreasView, self).get_context_data(**kwargs)

        all_area_names = set()
        context['posts'] = []

        for area_id in self.area_ids:
            ocd_division = area_id.replace(',', '/')
            # FIXME: there's quite a bit of repetition from
            # candidates/views/areas.py; do some DRY refactoring:
            area_extra = get_object_or_404(
                AreaExtra.objects \
                    .select_related('base', 'type') \
                    .prefetch_related('base__posts'),
                base__identifier=ocd_division,
                base__posts__extra__elections__current=True
            )
            area = area_extra.base
            all_area_names.add(area.name)
            for post in area.posts.all():
                post_extra = post.extra
                election = post_extra.elections.get(current=True)
                locked = post_extra.candidates_locked
                extra_qs = MembershipExtra.objects.select_related('election')
                current_candidacies, created = split_candidacies(
                    election,
                    post.memberships.prefetch_related(
                        Prefetch('extra', queryset=extra_qs)
                    ).select_related(
                        'person', 'person__extra', 'on_behalf_of',
                        'on_behalf_of__extra', 'organization'
                    ).all()
                )
                current_candidacies = group_candidates_by_party(
                    election,
                    current_candidacies,
                    party_list=election.party_lists_in_use,
                    max_people=election.default_party_list_members_to_show
                )
                context['posts'].append({
                    'election': election.slug,
                    'election_data': election,
                    'post_data': {
                        'id': post.extra.slug,
                        'label': post.label,
                    },
                    'candidates_locked': locked,
                    'candidate_list_edits_allowed':
                    get_edits_allowed(self.request.user, locked),
                    'candidacies': current_candidacies,
                    'add_candidate_form': NewPersonForm(
                        election=election.slug,
                        initial={
                            ('constituency_' + election.slug): post_extra.slug,
                            ('standing_' + election.slug): 'standing',
                        },
                        hidden_post_widget=True,
                    ),
                })

        context['all_area_names'] = ' — '.join(all_area_names)
        context['suppress_official_documents'] = True

        return context


class StPaulAreasOfTypeView(TemplateView):
    template_name = 'candidates/areas-of-type.html'

    def get_context_data(self, **kwargs):
        context = super(StPaulAreasOfTypeView, self).get_context_data(**kwargs)

        requested_area_type = kwargs['area_type']
        prefetch_qs = AreaExtra.objects.select_related('base').order_by('base__name')
        area_type = get_object_or_404(
            AreaType.objects \
                .prefetch_related(Prefetch('areas', queryset=prefetch_qs)),
            name=requested_area_type
        )
        areas = [
            (
                reverse(
                    'areas-view',
                    kwargs={
                        'type_and_area_ids': '{area_id}'.format(
                            area_id=re.sub(r'/', ',', area.base.identifier)
                        )
                    }
                ),
                area.base.name,
                requested_area_type,
            )
            for area in area_type.areas.all()
        ]
        context['areas'] = areas
        context['area_type'] = area_type
        return context
