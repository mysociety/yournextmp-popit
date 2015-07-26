from datetime import timedelta

from slugify import slugify

from django.views.decorators.cache import cache_control
from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.urlresolvers import reverse
from django.http import HttpResponse, HttpResponseRedirect
from django.utils.decorators import method_decorator
from django.utils.http import urlquote
from django.utils.translation import ugettext as _
from django.views.generic import TemplateView, FormView, View

from elections.mixins import ElectionMixin
from auth_helpers.views import GroupRequiredMixin
from .helpers import get_people_from_memberships, get_redirect_to_post
from .version_data import get_client_ip, get_change_metadata
from ..csv_helpers import list_to_csv
from ..forms import NewPersonForm, ToggleLockForm, ConstituencyRecordWinnerForm
from ..models import (
    get_post_label_from_post_id, PopItPerson, membership_covers_date,
    TRUSTED_TO_LOCK_GROUP_NAME, get_edits_allowed,
    RESULT_RECORDERS_GROUP_NAME, LoggedAction
)
from ..popit import PopItApiMixin, popit_unwrap_pagination
from ..election_specific import MAPIT_DATA, AREA_POST_DATA
from official_documents.models import OfficialDocument
from results.models import ResultEvent

from ..cache import get_post_cached, invalidate_posts

class ConstituencyDetailView(ElectionMixin, PopItApiMixin, TemplateView):
    template_name = 'candidates/constituency.html'

    @method_decorator(cache_control(max_age=(60 * 20)))
    def dispatch(self, *args, **kwargs):
        return super(ConstituencyDetailView, self).dispatch(
            *args, **kwargs
        )

    def get_context_data(self, **kwargs):
        context = super(ConstituencyDetailView, self).get_context_data(**kwargs)

        context['post_id'] = post_id = kwargs['post_id']
        mp_post = get_post_cached(self.api, post_id)

        documents_by_type = {}
        # Make sure that every available document type has a key in
        # the dictionary, even if there are no such documents.
        doc_lookup = {t[0]: (t[1], t[2]) for t in OfficialDocument.DOCUMENT_TYPES}
        for t in doc_lookup.values():
            documents_by_type[t] = []
        documents_for_post = OfficialDocument.objects.filter(post_id=post_id)
        for od in documents_for_post:
            documents_by_type[doc_lookup[od.document_type]].append(od)
        context['official_documents'] = documents_by_type.items()
        context['some_official_documents'] = documents_for_post.count()

        context['post_label'] = mp_post['result']['label']
        context['post_label_shorter'] = AREA_POST_DATA.shorten_post_label(
            self.election, context['post_label']
        )

        context['redirect_after_login'] = \
            urlquote(reverse('constituency', kwargs={
                'election': self.election,
                'post_id': post_id,
                'ignored_slug': slugify(context['post_label_shorter'])
            }))

        context['post_data'] = {
            k: v for k, v in mp_post['result'].items()
            if k in ('id', 'label')
        }

        context['candidates_locked'] = mp_post['result'].get(
            'candidates_locked', False
        )
        context['lock_form'] = ToggleLockForm(
            initial={
                'post_id': post_id,
                'lock': not context['candidates_locked'],
            },
        )
        context['candidate_list_edits_allowed'] = \
            get_edits_allowed(self.request.user, context['candidates_locked'])

        current_candidates, past_candidates = \
            get_people_from_memberships(
                self.election_data,
                mp_post['result']['memberships']
            )

        context['candidates_standing_again'] = \
            past_candidates.intersection(current_candidates)

        other_candidates = past_candidates - current_candidates

        # Now split those candidates into those that we know aren't
        # standing again, and those that we just don't know about:
        context['candidates_not_standing_again'] = \
            set(p for p in other_candidates if p.not_standing_in_election(self.election))

        context['candidates_might_stand_again'] = \
            set(p for p in other_candidates if not p.known_status_in_election(self.election))

        context['candidates'] = sorted(
            current_candidates,
            key=lambda c: c.last_name
        )

        context['show_retract_result'] = any(
            c.get_elected(self.election) is not None for c in context['candidates']
        )

        context['show_confirm_result'] = any(
            c.get_elected(self.election) is None for c in context['candidates']
        )

        context['add_candidate_form'] = NewPersonForm(
            election=self.election,
            initial={
                ('constituency_' + self.election): post_id,
                ('standing_' + self.election): 'standing',
            },
            hidden_post_widget=True,
        )

        return context


class ConstituencyDetailCSVView(ConstituencyDetailView):
    def render_to_response(self, context, **response_kwargs):
        all_people = [
            person.as_dict(self.election)
            for person in context['candidates']
        ]
        filename = "{election}-{constituency_slug}.csv".format(
            election=self.election,
            constituency_slug=slugify(context['constituency_name']),
        )
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="%s"' % filename
        response.write(list_to_csv(all_people))
        return response


class ConstituencyListView(ElectionMixin, PopItApiMixin, TemplateView):
    template_name = 'candidates/constituencies.html'

    def get_context_data(self, **kwargs):
        context = super(ConstituencyListView, self).get_context_data(**kwargs)
        context['all_constituencies'] = \
            MAPIT_DATA.areas_list_sorted_by_name[('WMC', 22)]
        return context


class ConstituencyLockView(ElectionMixin, GroupRequiredMixin, PopItApiMixin, View):
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
                    'election': self.election,
                    'post_id': post_id,
                    'ignored_slug': slugify(data['area']['name']),
                })
            )
        else:
            message = _('Invalid data POSTed to ConstituencyLockView')
            raise ValidationError(message)


class ConstituenciesUnlockedListView(ElectionMixin, PopItApiMixin, TemplateView):
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

class ConstituencyRecordWinnerView(ElectionMixin, GroupRequiredMixin, PopItApiMixin, FormView):

    form_class = ConstituencyRecordWinnerForm
    template_name = 'candidates/record-winner.html'
    required_group_name = RESULT_RECORDERS_GROUP_NAME

    def dispatch(self, request, *args, **kwargs):
        person_id = self.request.POST.get(
            'person_id',
            self.request.GET.get('person', '')
        )
        self.person = PopItPerson.create_from_popit(self.api, person_id)
        self.post_data = get_post_cached(self.api, self.kwargs['post_id'])['result']
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
        context['post_id'] = self.kwargs['post_id']
        context['constituency_name'] = self.post_data['label']
        context['person'] = self.person
        return context

    def form_valid(self, form):
        winner = self.person
        people_for_invalidation = set()
        for membership in self.post_data.get('memberships', []):
            candidate_role = self.election_data['candidate_membership_role']
            if membership.get('role') != candidate_role:
                continue
            if not membership_covers_date(
                    membership,
                    self.election_data['election_date']
            ):
                continue
            candidate = PopItPerson.create_from_popit(
                self.api, membership['person_id']['id']
            )
            elected = (candidate == winner)
            candidate.set_elected(elected, self.election)
            if elected:
                ResultEvent.create_from_popit_person(
                    candidate,
                    self.election,
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
        invalidate_posts([self.kwargs['post_id']])
        return get_redirect_to_post(
            self.election,
            self.post_data,
        )


class ConstituencyRetractWinnerView(ElectionMixin, GroupRequiredMixin, PopItApiMixin, View):

    required_group_name = RESULT_RECORDERS_GROUP_NAME
    http_method_names = ['post']

    def post(self, request, *args, **kwargs):
        post_id = self.kwargs['post_id']
        constituency_name = get_post_label_from_post_id(post_id)
        post = get_post_cached(self.api, post_id)['result']
        for membership in post.get('memberships', []):
            if membership.get('role') != self.election_data['candidate_membership_role']:
                continue
            if not membership_covers_date(
                    membership,
                    self.election_data['election_date']
            ):
                continue
            candidate = PopItPerson.create_from_popit(
                self.api, membership['person_id']['id']
            )
            candidate.set_elected(None, self.election)
            change_metadata = get_change_metadata(
                self.request,
                _('Result recorded in error, retracting')
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
        invalidate_posts([post_id])
        return HttpResponseRedirect(
            reverse(
                'constituency',
                kwargs={
                    'post_id': post_id,
                    'election': self.election,
                    'ignored_slug': slugify(constituency_name),
                }
            )
        )


def memberships_contain_winner(memberships, election_data):
    for m in memberships:
        correct_org = m.get('organization_id') == election_data['organization_id']
        day_after_election = election_data['election_date'] + timedelta(days=1)
        correct_start_date = m['start_date'] == str(day_after_election)
        if correct_org and correct_start_date:
            return True
    return False


class ConstituenciesDeclaredListView(ElectionMixin, PopItApiMixin, TemplateView):
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
            declared = memberships_contain_winner(
                post['memberships'],
                self.election_data
            )
            if declared:
                total_declared += 1
            constituencies.append((post, declared))
        constituencies.sort(key=lambda c: c[0]['area']['name'])
        context['constituencies'] = constituencies
        context['total_constituencies'] = total_constituencies
        context['total_left'] = total_constituencies - total_declared
        context['percent_done'] = (100 * total_declared) / total_constituencies
        return context
