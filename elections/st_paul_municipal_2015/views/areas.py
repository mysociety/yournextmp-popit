# -*- coding: utf-8 -*-

import re

from django.conf import settings
from django.core.urlresolvers import reverse
from django.core.cache import cache
from django.http import Http404, HttpResponseBadRequest, HttpResponseRedirect
from django.views.generic import TemplateView
from django.utils.text import slugify
from django.utils.http import urlquote
from django.utils.translation import ugettext as _

from candidates.cache import get_post_cached, UnknownPostException
from candidates.models.auth import get_edits_allowed
from candidates.popit import PopItApiMixin
from candidates.forms import NewPersonForm
from candidates.views import ConstituencyDetailView
from candidates.views.helpers import get_people_from_memberships

from elections.mixins import ElectionMixin

from official_documents.models import OfficialDocument

from .frontpage import get_cached_boundary

class StPaulAreasView(PopItApiMixin, TemplateView):
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
        area_dict = {}
        context['posts'] = []

        for area_id in self.area_ids:
            ocd_division = area_id.replace(',', '/')
            # Show candidates from the current elections:
            for election, election_data in settings.ELECTIONS_CURRENT:

                if election_data['ocd_division'] in ocd_division:

                    post_data = get_post_cached(self.api, area_id)['result']
                    boundary_data = get_cached_boundary(ocd_division)

                    all_area_names.add(boundary_data['objects'][0]['name'])

                    locked = post_data.get('candidates_locked', False)

                    current_candidates, _ = get_people_from_memberships(
                        election_data,
                        post_data['memberships'],
                    )

                    if not area_dict.get(ocd_division):
                        area_dict[ocd_division] = 'done'

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
                                    ('constituency_' + election): area_id,
                                    ('standing_' + election): 'standing',
                                },
                                hidden_post_widget=True,
                            ),
                        })

        context['all_area_names'] = u' — '.join(all_area_names)
        context['suppress_official_documents'] = True

        return context

class StPaulDistrictDetailView(ConstituencyDetailView):

    template_name = 'st_paul_municipal_2015/districts.html'

    def get_context_data(self, **kwargs):
        context = super(StPaulDistrictDetailView, self).get_context_data(**kwargs)

        # context['electionleaflets_url'] = \
        #     get_electionleaflets_url(
        #         context['post_id'],
        #         context['post_label_shorter']
        #     )

        # context['meetyournextmp_url'] = \
        #     u'https://meetyournextmp.com/linktoseat.html?mapitid={}'.format(
        #         context['post_id']
        #     )
        return context

class StPaulAreasOfTypeView(PopItApiMixin, TemplateView):
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
