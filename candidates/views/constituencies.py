import re
import unicodedata

from slugify import slugify

from django.views.decorators.cache import cache_control
from django.core.exceptions import ValidationError
from django.core.urlresolvers import reverse
from django.http import HttpResponse, HttpResponseRedirect, Http404
from django.utils.decorators import method_decorator
from django.utils.http import urlquote
from django.views.generic import TemplateView, FormView, View

from auth_helpers.views import GroupRequiredMixin, user_in_group
from .version_data import get_client_ip, get_change_metadata
from ..csv_helpers import list_to_csv
from ..forms import NewPersonForm, ToggleLockForm, ConstituencyRecordWinnerForm
from ..models import (
    get_constituency_name_from_mapit_id, PopItPerson, membership_covers_date,
    election_date_2010, election_date_2015, TRUSTED_TO_LOCK_GROUP_NAME,
    RESULT_RECORDERS_GROUP_NAME, LoggedAction
)
from ..popit import PopItApiMixin, popit_unwrap_pagination
from ..static_data import MapItData
from official_documents.models import OfficialDocument
from results.models import ResultEvent

from ..cache import get_post_cached, invalidate_posts

# From http://stackoverflow.com/a/517974/223092
def strip_accents(s):
    return u"".join(
        c for c in unicodedata.normalize('NFKD', s)
        if not unicodedata.combining(c)
    )

def get_electionleaflets_url(mapit_area_id, constituency_name):
    """Generate an electionleaflets.org URL from a constituency name

    >>> get_electionleaflets_url(u"66115", u"Ynys M\u00F4n")
    u'http://electionleaflets.org/constituencies/66115/ynys_mon/'
    >>> get_electionleaflets_url(u"66056", u"Ashton-under-Lyne")
    u'http://electionleaflets.org/constituencies/66056/ashton_under_lyne/'
    >>> get_electionleaflets_url(u"14403", u"Ayr, Carrick and Cumnock")
    u'http://electionleaflets.org/constituencies/14403/ayr_carrick_and_cumnock/'
    """
    result = strip_accents(constituency_name)
    result = result.lower()
    result = re.sub(r'[^a-z]+', ' ', result)
    result = re.sub(r'\s+', ' ', result).strip()
    slug = result.replace(' ', '_')
    url_format = u'http://electionleaflets.org/constituencies/{area_id}/{slug}/'
    return url_format.format(area_id=mapit_area_id, slug=slug)


class ConstituencyDetailView(PopItApiMixin, TemplateView):
    template_name = 'candidates/constituency.html'

    @method_decorator(cache_control(max_age=(60 * 20)))
    def dispatch(self, *args, **kwargs):
        return super(ConstituencyDetailView, self).dispatch(
            *args, **kwargs
        )

    def get_context_data(self, **kwargs):
        context = super(ConstituencyDetailView, self).get_context_data(**kwargs)

        context['mapit_area_id'] = mapit_area_id = kwargs['mapit_area_id']
        context['constituency_name'] = \
            get_constituency_name_from_mapit_id(mapit_area_id)

        if not context['constituency_name']:
            raise Http404("Constituency not found")

        context['electionleaflets_url'] = \
            get_electionleaflets_url(mapit_area_id, context['constituency_name'])

        context['meetyournextmp_url'] = \
            u'https://meetyournextmp.com/linktoseat.html?mapitid={}'.format(mapit_area_id)

        context['redirect_after_login'] = \
            urlquote(reverse('constituency', kwargs={
                'mapit_area_id': mapit_area_id,
                'ignored_slug': slugify(context['constituency_name'])
            }))

        context['nomination_papers'] = OfficialDocument.objects.filter(
            document_type=OfficialDocument.NOMINATION_PAPER,
            mapit_id=mapit_area_id,
        )

        mp_post = get_post_cached(self.api, mapit_area_id)

        context['candidates_locked'] = mp_post['result'].get(
            'candidates_locked', False
        )
        context['lock_form'] = ToggleLockForm(
            initial={
                'post_id': mapit_area_id,
                'lock': not context['candidates_locked'],
            },
        )
        context['candidate_list_edits_allowed'] = \
            self.request.user.is_authenticated() and (
                user_in_group(self.request.user, TRUSTED_TO_LOCK_GROUP_NAME) or
                (not context['candidates_locked'])
            )

        current_candidates = set()
        past_candidates = set()

        for membership in mp_post['result']['memberships']:
            if not membership.get('role') == "Candidate":
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

        context['candidates_2015'] = sorted(
            current_candidates,
            key=lambda c: c.last_name
        )

        context['show_retract_result'] = any(
            c.get_elected() is not None for c in context['candidates_2015']
        )

        context['add_candidate_form'] = NewPersonForm(
            initial={'constituency': mapit_area_id}
        )

        return context


class ConstituencyDetailCSVView(ConstituencyDetailView):
    def render_to_response(self, context, **response_kwargs):
        all_people = []
        for person in context['candidates_2015']:
            all_people.append(person.as_dict())
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


class ConstituencyLockView(GroupRequiredMixin, PopItApiMixin, View):
    required_group_name = TRUSTED_TO_LOCK_GROUP_NAME

    http_method_names = ['post']

    def post(self, request, *args, **kwargs):
        form = ToggleLockForm(data=self.request.POST)
        if form.is_valid():
            post_id = form.cleaned_data['post_id']
            data = self.api.posts(post_id). \
                get(embed='')['result']
            lock = form.cleaned_data['lock']
            data['candidates_locked'] = lock
            if lock:
                suffix = '-lock'
                pp = 'Locked'
            else:
                suffix = '-unlock'
                pp = 'Unlocked'
            message = pp + u' constituency {0} ({1})'.format(
                data['area']['name'], data['id']
            )
            self.api.posts(post_id).put(data)
            invalidate_posts([post_id])
            LoggedAction.objects.create(
                user=self.request.user,
                action_type=('constituency' + suffix),
                ip_address=get_client_ip(self.request),
                popit_person_new_version='',
                popit_person_id='',
                source=message,
            )
            return HttpResponseRedirect(
                reverse('constituency', kwargs={
                    'mapit_area_id': post_id,
                    'ignored_slug': slugify(data['area']['name']),
                })
            )
        else:
            message = 'Invalid data POSTed to ConstituencyLockView'
            raise ValidationError(message)


class ConstituenciesUnlockedListView(PopItApiMixin, TemplateView):
    template_name = 'candidates/constituencies-unlocked.html'

    def get_context_data(self, **kwargs):
        context = super(ConstituenciesUnlockedListView, self).get_context_data(**kwargs)
        total_constituencies = 0
        total_locked = 0
        keys = ('locked', 'unlocked')
        for k in keys:
            context[k] = []
        for post in popit_unwrap_pagination(
                self.api.posts,
                embed='',
                per_page=100,
        ):
            total_constituencies += 1
            if post.get('candidates_locked'):
                context_field = 'locked'
                total_locked += 1
            else:
                context_field = 'unlocked'
            context[context_field].append(
                {
                    'id': post['id'],
                    'name': post['area']['name'],
                }
            )
        for k in keys:
            context[k].sort(key=lambda c: c['name'])
        context['total_constituencies'] = total_constituencies
        context['total_left'] = total_constituencies - total_locked
        context['percent_done'] = (100 * total_locked) / total_constituencies
        return context

class ConstituencyRecordWinnerView(GroupRequiredMixin, PopItApiMixin, FormView):

    form_class = ConstituencyRecordWinnerForm
    template_name = 'candidates/record-winner.html'
    required_group_name = RESULT_RECORDERS_GROUP_NAME

    def dispatch(self, request, *args, **kwargs):
        person_id = self.request.POST.get(
            'person_id',
            self.request.GET.get('person', '')
        )
        self.person = PopItPerson.create_from_popit(self.api, person_id)
        self.mapit_area_id = self.kwargs['mapit_area_id']
        self.constituency_name = \
            get_constituency_name_from_mapit_id(self.mapit_area_id)
        return super(ConstituencyRecordWinnerView, self). \
            dispatch(request, *args, **kwargs)

    def get_initial(self):
        initial = super(ConstituencyRecordWinnerView, self). \
            get_initial()
        initial['person_id'] = self.person.id
        return initial

    def get_context_data(self, **kwargs):
        context = super(ConstituencyRecordWinnerView, self). \
            get_context_data(**kwargs)
        context['mapit_area_id'] = self.mapit_area_id
        context['constituency_name'] = self.constituency_name
        context['person'] = self.person
        return context

    def form_valid(self, form):
        winner = self.person
        post = get_post_cached(self.api, self.mapit_area_id)['result']
        people_for_invalidation = set()
        for membership in post.get('memberships', []):
            if membership.get('role') != 'Candidate':
                continue
            if not membership_covers_date(membership, election_date_2015):
                continue
            candidate = PopItPerson.create_from_popit(
                self.api, membership['person_id']['id']
            )
            elected = (candidate == winner)
            candidate.set_elected(elected)
            if elected:
                ResultEvent.create_from_popit_person(
                    candidate,
                    '2015',
                    form.cleaned_data['source'],
                    self.request.user,
                )
            change_metadata = get_change_metadata(
                self.request,
                form.cleaned_data['source']
            )
            candidate.record_version(change_metadata)
            candidate.save_to_popit(self.api)
            candidate.invalidate_cache_entries()
            LoggedAction.objects.create(
                user=self.request.user,
                action_type='set-candidate-' + \
                    ('elected' if elected else 'not-elected'),
                ip_address=get_client_ip(self.request),
                popit_person_new_version=change_metadata['version_id'],
                popit_person_id=candidate.id,
                source=change_metadata['information_source'],
            )
            people_for_invalidation.add(candidate)
        for person_for_invalidation in people_for_invalidation:
            person_for_invalidation.invalidate_cache_entries()
        # This shouldn't be necessary since invalidating the people
        # will invalidate the post
        invalidate_posts([self.mapit_area_id])
        return HttpResponseRedirect(
            reverse(
                'constituency',
                kwargs={
                    'mapit_area_id': self.mapit_area_id,
                    'ignored_slug': slugify(self.constituency_name),
                }
            )
        )


class ConstituencyRetractWinnerView(GroupRequiredMixin, PopItApiMixin, View):

    required_group_name = RESULT_RECORDERS_GROUP_NAME
    http_method_names = ['post']

    def post(self, request, *args, **kwargs):
        mapit_area_id = self.kwargs['mapit_area_id']
        constituency_name = get_constituency_name_from_mapit_id(mapit_area_id)
        post = get_post_cached(self.api, mapit_area_id)['result']
        for membership in post.get('memberships', []):
            if membership.get('role') != 'Candidate':
                continue
            if not membership_covers_date(membership, election_date_2015):
                continue
            candidate = PopItPerson.create_from_popit(
                self.api, membership['person_id']['id']
            )
            candidate.set_elected(None)
            change_metadata = get_change_metadata(
                self.request,
                'Result recorded in error, retracting'
            )
            candidate.record_version(change_metadata)
            candidate.save_to_popit(self.api)
            candidate.invalidate_cache_entries()
            LoggedAction.objects.create(
                user=self.request.user,
                action_type='retract-result',
                ip_address=get_client_ip(self.request),
                popit_person_new_version=change_metadata['version_id'],
                popit_person_id=candidate.id,
                source=change_metadata['information_source'],
            )
        # This shouldn't be necessary since invalidating the people
        # will invalidate the post
        invalidate_posts([mapit_area_id])
        return HttpResponseRedirect(
            reverse(
                'constituency',
                kwargs={
                    'mapit_area_id': mapit_area_id,
                    'ignored_slug': slugify(constituency_name),
                }
            )
        )


def memberships_contain_winner(memberships):
    for m in memberships:
        if m.get('organization_id') == 'commons' and m['start_date'] == "2015-05-08":
            return True
    return False


class ConstituenciesDeclaredListView(PopItApiMixin, TemplateView):
    template_name = 'candidates/constituencies-declared.html'

    def get_context_data(self, **kwargs):
        context = super(ConstituenciesDeclaredListView, self).get_context_data(**kwargs)
        total_constituencies = 0
        total_declared = 0
        constituencies = []
        for post in popit_unwrap_pagination(
                self.api.posts,
                embed='membership',
                per_page=100,
        ):
            total_constituencies += 1
            declared = memberships_contain_winner(post['memberships'])
            if declared:
                total_declared += 1
            constituencies.append((post, declared))
        constituencies.sort(key=lambda c: c[0]['area']['name'])
        context['constituencies'] = constituencies
        context['total_constituencies'] = total_constituencies
        context['total_left'] = total_constituencies - total_declared
        context['percent_done'] = (100 * total_declared) / total_constituencies
        return context
