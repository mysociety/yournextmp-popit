import re
import unicodedata

from slugify import slugify

from django.core.urlresolvers import reverse
from django.http import HttpResponse, Http404
from django.utils.http import urlquote
from django.views.generic import TemplateView

from ..csv_helpers import list_to_csv
from ..forms import NewPersonForm
from ..models import (
    get_constituency_name_from_mapit_id, PopItPerson, membership_covers_date,
    election_date_2010, election_date_2015
)
from ..popit import PopItApiMixin
from ..static_data import MapItData

# From http://stackoverflow.com/a/517974/223092
def strip_accents(s):
    return u"".join(
        c for c in unicodedata.normalize('NFKD', s)
        if not unicodedata.combining(c)
    )

def get_electionleaflets_url(constituency_name):
    """Generate an electionleaflets.org URL from a constituency name

    >>> get_electionleaflets_url(u"Ynys M\u00F4n")
    u'http://electionleaflets.org/constituencies/ynys_mon/'
    >>> get_electionleaflets_url(u"Ashton-under-Lyne")
    u'http://electionleaflets.org/constituencies/ashton_under_lyne/'
    >>> get_electionleaflets_url(u"Ayr, Carrick and Cumnock")
    u'http://electionleaflets.org/constituencies/ayr_carrick_and_cumnock/'
    """
    result = strip_accents(constituency_name)
    result = result.lower()
    result = re.sub(r'[^a-z]+', ' ', result)
    result = re.sub(r'\s+', ' ', result).strip()
    slug = result.replace(' ', '_')
    return u'http://electionleaflets.org/constituencies/{}/'.format(slug)



class ConstituencyDetailView(PopItApiMixin, TemplateView):
    template_name = 'candidates/constituency.html'

    def get_context_data(self, **kwargs):
        context = super(ConstituencyDetailView, self).get_context_data(**kwargs)

        context['mapit_area_id'] = mapit_area_id = kwargs['mapit_area_id']
        context['constituency_name'] = \
            get_constituency_name_from_mapit_id(mapit_area_id)

        if not context['constituency_name']:
            raise Http404("Constituency not found")

        context['electionleaflets_url'] = \
            get_electionleaflets_url(context['constituency_name'])

        context['meetyournextmp_url'] = u'https://meetyournextmp.com/linktoseat.html?mapitid=' . mapit_area_id ;

        context['redirect_after_login'] = \
            urlquote(reverse('constituency', kwargs={
                'mapit_area_id': mapit_area_id,
                'ignored_slug': slugify(context['constituency_name'])
            }))

        mp_post = self.api.posts(mapit_area_id).get(
            embed='membership.person.membership.organization')

        current_candidates = set()
        past_candidates = set()

        for membership in mp_post['result']['memberships']:
            if not membership['role'] == "Candidate":
                continue
            person = PopItPerson.create_from_dict(membership['person_id'])
            if membership_covers_date(membership, election_date_2010):
                past_candidates.add(person)
            elif membership_covers_date(membership, election_date_2015):
                current_candidates.add(person)
            else:
                raise ValueError("Candidate membership doesn't cover any \
                                  known election date")

        context['candidates_2010_standing_again'] = \
            past_candidates.intersection(current_candidates)

        other_candidates_2010 = past_candidates - current_candidates

        # Now split those candidates into those that we know aren't
        # standing again, and those that we just don't know about:
        context['candidates_2010_not_standing_again'] = \
            set(p for p in other_candidates_2010 if p.not_standing_in_2015)

        context['candidates_2010_might_stand_again'] = \
            set(p for p in other_candidates_2010 if not p.known_status_in_2015)

        context['candidates_2015'] = current_candidates

        context['add_candidate_form'] = NewPersonForm(
            initial={'constituency': mapit_area_id}
        )

        return context

class ConstituencyDetailCSVView(ConstituencyDetailView):
    def render_to_response(self, context, **response_kwargs):
        all_people = []
        for person in context['candidates_2015']:
            all_people.append(person.as_dict)
        filename = "%s.csv" % slugify(context['constituency_name'])
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="%s"' % filename
        response.write(list_to_csv(all_people))
        return response



class ConstituencyListView(PopItApiMixin, TemplateView):
    template_name = 'candidates/constituencies.html'

    def get_context_data(self, **kwargs):
        context = super(ConstituencyListView, self).get_context_data(**kwargs)
        context['all_constituencies'] = \
            MapItData.constituencies_2010_name_sorted
        return context
