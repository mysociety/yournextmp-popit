# -*- coding: utf-8 -*-

import re

from django.conf import settings
from django.core.urlresolvers import reverse
from django.http import Http404, HttpResponseBadRequest
from django.views.generic import TemplateView
from django.utils.text import slugify
from django.utils.translation import ugettext as _

from candidates.cache import get_post_cached, UnknownPostException
from candidates.models.auth import get_edits_allowed
from candidates.popit import PopItApiMixin

from ..election_specific import AREA_POST_DATA, MAPIT_DATA
from ..forms import NewPersonForm
from .helpers import get_people_from_memberships, group_people_by_party

class AreasView(PopItApiMixin, TemplateView):
    template_name = 'candidates/areas.html'

    def get(self, request, *args, **kwargs):
        self.types_and_areas = []
        for type_and_area in kwargs['type_and_area_ids'].split(','):
            m = re.search(r'^([A-Z0-9]+)-(\d+)$', type_and_area)
            if not m:
                message = _("Malformed type and area: '{0}'")
                return HttpResponseBadRequest(message.format(type_and_area))
            self.types_and_areas.append(m.groups())
        try:
            view = super(AreasView, self).get(request, *args, **kwargs)
        except UnknownPostException:
            message = _("Unknown post for types and areas: '{0}'")
            return HttpResponseBadRequest(message.format(kwargs['type_and_area_ids']))
        return view

    def get_context_data(self, **kwargs):
        context = super(AreasView, self).get_context_data(**kwargs)
        all_area_names = set()
        context['posts'] = []
        for mapit_type, area_id in self.types_and_areas:
            # Show candidates from the current elections:
            for election, election_data in settings.ELECTIONS_CURRENT:
                mapit_generation = election_data['mapit_generation']
                if mapit_type in election_data['mapit_types']:
                    mapit_tuple = (mapit_type, mapit_generation)
                    post_id = AREA_POST_DATA.get_post_id(election, mapit_type, area_id)
                    post_data = get_post_cached(self.api, post_id)['result']
                    area_name = MAPIT_DATA.areas_by_id[mapit_tuple][area_id]['name']
                    all_area_names.add(area_name)
                    locked = post_data.get('candidates_locked', False)
                    current_candidates, _ = get_people_from_memberships(
                        election_data,
                        post_data['memberships']
                    )
                    current_candidates = group_people_by_party(
                        election,
                        current_candidates,
                        party_list=election_data.get('party_lists_in_use')
                    )
                    context['posts'].append({
                        'election': election,
                        'election_data': election_data,
                        'post_data': post_data,
                        'candidates_locked': locked,
                        'candidate_list_edits_allowed':
                        get_edits_allowed(self.request.user, locked),
                        'candidates': current_candidates,
                        'add_candidate_form': NewPersonForm(
                            election=election,
                            initial={
                                ('constituency_' + election): post_id,
                                ('standing_' + election): 'standing',
                            },
                            hidden_post_widget=True,
                        ),
                    })
        context['all_area_names'] = u' — '.join(all_area_names)
        context['suppress_official_documents'] = True
        return context

class AreasOfTypeView(PopItApiMixin, TemplateView):
    template_name = 'candidates/areas-of-type.html'

    def get_context_data(self, **kwargs):
        context = super(AreasOfTypeView, self).get_context_data(**kwargs)
        requested_mapit_type = kwargs['mapit_type']
        all_mapit_tuples = set(
            (mapit_type, election_data['mapit_generation'])
            for election, election_data in settings.ELECTIONS_CURRENT
            for mapit_type in election_data['mapit_types']
            if mapit_type == requested_mapit_type
        )
        if not all_mapit_tuples:
            raise Http404(_("Area '{0}' not found").format(requested_mapit_type))
        if len(all_mapit_tuples) > 1:
            message = _("Multiple MapIt generations for type {mapit_type} found")
            raise Exception(message.format(mapit_type=requested_mapit_type))
        mapit_tuple = list(all_mapit_tuples)[0]
        areas = [
            (
                reverse(
                    'areas-view',
                    kwargs={
                        'type_and_area_ids': '{type}-{area_id}'.format(
                            type=requested_mapit_type,
                            area_id=area['id']
                        ),
                        'ignored_slug': slugify(area['name'])
                    }
                ),
                area['name'],
                area['type_name'],
            )
            for area in MAPIT_DATA.areas_by_id[mapit_tuple].values()
        ]
        areas.sort(key=lambda a: a[1])
        context['areas'] = areas
        context['area_type_name'] = _('[No areas found]')
        if areas:
            context['area_type_name'] = areas[0][2]
        return context
