from __future__ import unicode_literals

from datetime import timedelta

from slugify import slugify

from django.views.decorators.cache import cache_control
from django.core.exceptions import ValidationError
from django.core.urlresolvers import reverse
from django.http import HttpResponse, HttpResponseRedirect, Http404
from django.utils.decorators import method_decorator
from django.utils.http import urlquote
from django.utils.translation import ugettext as _
from django.views.generic import TemplateView, FormView, View
from django.shortcuts import get_object_or_404
from django.db import transaction
from django.db.models import Prefetch

from elections.mixins import ElectionMixin
from auth_helpers.views import GroupRequiredMixin
from .helpers import (
    get_party_people_for_election_from_memberships,
    split_candidacies, get_redirect_to_post,
    group_candidates_by_party, get_person_form_fields,
    get_winning_candidates
)
from .version_data import get_client_ip, get_change_metadata
from ..csv_helpers import list_to_csv
from ..forms import NewPersonForm, ToggleLockForm, ConstituencyRecordWinnerForm
from ..models import (
    TRUSTED_TO_LOCK_GROUP_NAME, get_edits_allowed,
    RESULT_RECORDERS_GROUP_NAME, LoggedAction, PostExtra, OrganizationExtra,
    MembershipExtra, PartySet, PostExtraElection
)
from official_documents.models import OfficialDocument
from results.models import ResultEvent

from popolo.models import Membership, Post, Organization, Person


def get_max_winners(post, election):
    max_winners = election.people_elected_per_post
    post_extra_election = PostExtraElection.objects.filter(
        postextra__base=post,
        election=election,
        winner_count__isnull=False,
    ).first()
    if post_extra_election:
        max_winners = post_extra_election.winner_count

    return max_winners


class ConstituencyDetailView(ElectionMixin, TemplateView):
    template_name = 'candidates/constituency.html'

    @method_decorator(cache_control(max_age=(60 * 20)))
    def dispatch(self, *args, **kwargs):
        return super(ConstituencyDetailView, self).dispatch(
            *args, **kwargs
        )

    def get_context_data(self, **kwargs):
        from ..election_specific import shorten_post_label
        context = super(ConstituencyDetailView, self).get_context_data(**kwargs)

        context['post_id'] = post_id = kwargs['post_id']
        mp_post = get_object_or_404(
            Post.objects.select_related('extra'),
            extra__slug=post_id
        )

        documents_by_type = {}
        # Make sure that every available document type has a key in
        # the dictionary, even if there are no such documents.
        doc_lookup = {t[0]: (t[1], t[2]) for t in OfficialDocument.DOCUMENT_TYPES}
        for t in doc_lookup.values():
            documents_by_type[t] = []
        documents_for_post = OfficialDocument.objects.filter(post_id=mp_post.id)
        for od in documents_for_post:
            documents_by_type[doc_lookup[od.document_type]].append(od)
        context['official_documents'] = documents_by_type.items()
        context['some_official_documents'] = documents_for_post.count()

        context['post_label'] = mp_post.label
        context['post_label_shorter'] = shorten_post_label(context['post_label'])

        context['redirect_after_login'] = \
            urlquote(reverse('constituency', kwargs={
                'election': self.election,
                'post_id': post_id,
                'ignored_slug': slugify(context['post_label_shorter'])
            }))

        context['post_data'] = {
            'id': mp_post.extra.slug,
            'label': mp_post.label
        }

        context['candidates_locked'] = False
        if hasattr(mp_post, 'extra'):
            context['candidates_locked'] = mp_post.extra.candidates_locked

        context['lock_form'] = ToggleLockForm(
            initial={
                'post_id': post_id,
                'lock': not context['candidates_locked'],
            },
        )
        context['candidate_list_edits_allowed'] = \
            get_edits_allowed(self.request.user, context['candidates_locked'])

        extra_qs = MembershipExtra.objects.select_related('election')
        current_candidacies, past_candidacies = \
            split_candidacies(
                self.election_data,
                mp_post.memberships.prefetch_related(
                    Prefetch('extra', queryset=extra_qs)
                ).select_related(
                    'person', 'person__extra', 'on_behalf_of',
                    'on_behalf_of__extra', 'organization'
                ).all()
            )

        winners = get_winning_candidates(current_candidacies)
        current_candidates = set(c.person for c in current_candidacies)
        past_candidates = set(c.person for c in past_candidacies)

        other_candidates = past_candidates - current_candidates

        # Now split those candidates into those that we know aren't
        # standing again, and those that we just don't know about.
        not_standing_candidates = set(
            p for p in other_candidates
            if self.election_data in p.extra.not_standing.all()
        )
        might_stand_candidates = set(
            p for p in other_candidates
            if self.election_data not in p.extra.not_standing.all()
        )

        not_standing_candidacies = [c for c in past_candidacies
                                    if c.person in not_standing_candidates]
        might_stand_candidacies = [c for c in past_candidacies
                                   if c.person in might_stand_candidates]

        context['candidacies_not_standing_again'] = \
            group_candidates_by_party(
                self.election_data,
                not_standing_candidacies,
                party_list=self.election_data.party_lists_in_use,
                max_people=self.election_data.default_party_list_members_to_show
            )

        context['candidacies_might_stand_again'] = \
            group_candidates_by_party(
                self.election_data,
                might_stand_candidacies,
                party_list=self.election_data.party_lists_in_use,
                max_people=self.election_data.default_party_list_members_to_show
            )

        context['candidacies'] = group_candidates_by_party(
            self.election_data,
            current_candidacies,
            party_list=self.election_data.party_lists_in_use,
            max_people=self.election_data.default_party_list_members_to_show
        )

        context['show_retract_result'] = False
        number_of_winners = 0
        for c in current_candidacies:
            if c.extra.elected:
                number_of_winners += 1
            if c.extra.elected is not None:
                context['show_retract_result'] = True

        context['winners'] = winners
        max_winners = get_max_winners(mp_post, self.election_data)
        context['show_confirm_result'] = (max_winners < 0) \
            or number_of_winners < max_winners

        context['add_candidate_form'] = NewPersonForm(
            election=self.election,
            initial={
                ('constituency_' + self.election): post_id,
                ('standing_' + self.election): 'standing',
            },
            hidden_post_widget=True,
        )

        context = get_person_form_fields(
            context,
            context['add_candidate_form']
        )
        return context


class ConstituencyDetailCSVView(ElectionMixin, View):

    http_method_names = ['get']

    def get(self, request, *args, **kwargs):
        post = Post.objects \
            .select_related('extra') \
            .get(extra__slug=kwargs['post_id'])
        all_people = [
            me.base.person.extra.as_dict(self.election_data)
            for me in
            MembershipExtra.objects \
                .filter(
                    election=self.election_data,
                    base__post=post
                ) \
                .select_related('base__person') \
                .prefetch_related('base__person__extra')
        ]

        filename = "{election}-{constituency_slug}.csv".format(
            election=self.election,
            constituency_slug=slugify(post.extra.short_label),
        )
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="%s"' % filename
        response.write(list_to_csv(all_people))
        return response


class ConstituencyListView(ElectionMixin, TemplateView):
    template_name = 'candidates/constituencies.html'

    def get_context_data(self, **kwargs):
        context = super(ConstituencyListView, self).get_context_data(**kwargs)
        context['all_constituencies'] = \
            PostExtra.objects.filter(
                elections__slug=self.election
            ).order_by('base__label').select_related('base')

        return context


class ConstituencyLockView(ElectionMixin, GroupRequiredMixin, View):
    required_group_name = TRUSTED_TO_LOCK_GROUP_NAME

    http_method_names = ['post']

    def post(self, request, *args, **kwargs):
        form = ToggleLockForm(data=self.request.POST)
        if form.is_valid():
            post_id = form.cleaned_data['post_id']
            with transaction.atomic():
                post = get_object_or_404(Post, extra__slug=post_id)
                lock = form.cleaned_data['lock']
                post.extra.candidates_locked = lock
                post.extra.save()
                post_name = post.extra.short_label
                if lock:
                    suffix = '-lock'
                    pp = 'Locked'
                else:
                    suffix = '-unlock'
                    pp = 'Unlocked'
                message = pp + ' constituency {0} ({1})'.format(
                    post_name, post.id
                )

                LoggedAction.objects.create(
                    user=self.request.user,
                    action_type=('constituency' + suffix),
                    ip_address=get_client_ip(self.request),
                    source=message,
                )
            return HttpResponseRedirect(
                reverse('constituency', kwargs={
                    'election': self.election,
                    'post_id': post_id,
                    'ignored_slug': slugify(post_name),
                })
            )
        else:
            message = _('Invalid data POSTed to ConstituencyLockView')
            raise ValidationError(message)


class ConstituenciesUnlockedListView(ElectionMixin, TemplateView):
    template_name = 'candidates/constituencies-unlocked.html'

    def get_context_data(self, **kwargs):
        context = super(ConstituenciesUnlockedListView, self).get_context_data(**kwargs)
        total_constituencies = 0
        total_locked = 0
        keys = ('locked', 'unlocked')
        for k in keys:
            context[k] = []
        posts = Post.objects.select_related('extra').all()
        for post in posts:
            total_constituencies += 1
            if post.extra.candidates_locked:
                context_field = 'locked'
                total_locked += 1
            else:
                context_field = 'unlocked'
            context[context_field].append(
                {
                    'id': post.extra.slug,
                    'name': post.extra.short_label,
                }
            )
        for k in keys:
            context[k].sort(key=lambda c: c['name'])
        context['total_constituencies'] = total_constituencies
        context['total_left'] = total_constituencies - total_locked
        context['percent_done'] = (100 * total_locked) // total_constituencies
        return context

class ConstituencyRecordWinnerView(ElectionMixin, GroupRequiredMixin, FormView):

    form_class = ConstituencyRecordWinnerForm
    # TODO: is this template ever used?
    template_name = 'candidates/record-winner.html'
    required_group_name = RESULT_RECORDERS_GROUP_NAME

    def dispatch(self, request, *args, **kwargs):
        person_id = self.request.POST.get(
            'person_id',
            self.request.GET.get('person', '')
        )
        self.person = get_object_or_404(Person, id=person_id)
        self.post_data = get_object_or_404(Post, extra__slug=self.kwargs['post_id'])

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
        context['constituency_name'] = self.post_data.label
        context['person'] = self.person
        return context

    def form_valid(self, form):
        change_metadata = get_change_metadata(
            self.request,
            form.cleaned_data['source']
        )

        with transaction.atomic():
            number_of_existing_winners = self.post_data.memberships.filter(
                extra__elected=True,
                extra__election=self.election_data
            ).count()
            max_winners = get_max_winners(self.post_data, self.election_data)
            if max_winners >= 0 and number_of_existing_winners >= max_winners:
                msg = "There were already {n} winners of {post_label}" \
                    "and the maximum in election {election_name} is {max}"
                raise Exception(msg.format(
                    n=number_of_existing_winners,
                    post_label=self.post_data.label,
                    election_name=self.election_data.name,
                    max=self.election_data.people_elected_per_post
                ))
            # So now we know we can set this person as the winner:
            candidate_role = self.election_data.candidate_membership_role
            membership_new_winner = Membership.objects.get(
                role=candidate_role,
                post=self.post_data,
                person=self.person,
                extra__election=self.election_data,
            )
            membership_new_winner.extra.elected = True
            membership_new_winner.extra.save()

            ResultEvent.objects.create(
                election=self.election_data,
                winner=self.person,
                winner_person_name=self.person.name,
                post_id=self.post_data.extra.slug,
                post_name=self.post_data.label,
                winner_party_id=membership_new_winner.on_behalf_of.extra.slug,
                source=form.cleaned_data['source'],
                user=self.request.user,
            )

            self.person.extra.record_version(change_metadata)
            self.person.save()

            LoggedAction.objects.create(
                user=self.request.user,
                action_type='set-candidate-elected',
                ip_address=get_client_ip(self.request),
                popit_person_new_version=change_metadata['version_id'],
                person=self.person,
                source=change_metadata['information_source'],
            )

            # Now, if the current number of winners is equal to the
            # maximum number of winners, we can set everyone else as
            # "not elected".
            if max_winners >= 0:
                max_reached = (max_winners == (number_of_existing_winners + 1))
                if max_reached:
                    losing_candidacies = self.post_data.memberships.filter(
                        extra__election=self.election_data,
                    ).exclude(extra__elected=True)
                    for candidacy in losing_candidacies:
                        if candidacy.extra.elected != False:
                            candidacy.extra.elected = False
                            candidacy.extra.save()
                            candidate = candidacy.person
                            change_metadata = get_change_metadata(
                                self.request,
                                _('Setting as "not elected" by implication')
                            )
                            candidate.extra.record_version(change_metadata)
                            candidate.save()

        return get_redirect_to_post(
            self.election,
            self.post_data,
        )


class ConstituencyRetractWinnerView(ElectionMixin, GroupRequiredMixin, View):

    required_group_name = RESULT_RECORDERS_GROUP_NAME
    http_method_names = ['post']

    def post(self, request, *args, **kwargs):
        post_id = self.kwargs['post_id']
        post = get_object_or_404(Post, extra__slug=post_id)
        constituency_name = post.extra.short_label

        with transaction.atomic():
            all_candidacies = post.memberships.filter(
                role=self.election_data.candidate_membership_role,
                extra__election=self.election_data,
            )
            for candidacy in all_candidacies.all():
                if candidacy.extra.elected is not None:
                    candidacy.extra.elected = None
                    candidacy.extra.save()
                    candidate = candidacy.person
                    change_metadata = get_change_metadata(
                        self.request,
                        _('Result recorded in error, retracting')
                    )
                    candidate.extra.record_version(change_metadata)
                    candidate.save()

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


class ConstituenciesDeclaredListView(ElectionMixin, TemplateView):
    template_name = 'candidates/constituencies-declared.html'

    def get_context_data(self, **kwargs):
        context = super(ConstituenciesDeclaredListView, self).get_context_data(**kwargs)
        total_constituencies = 0
        total_declared = 0
        constituency_declared = []
        constituency_seen = {}
        constituencies = []
        total_constituencies = Post.objects.all().count()
        for membership in Membership.objects.select_related('post', 'post__area', 'post__extra').filter(
            post__isnull=False,
            extra__election_id=self.election_data.id,
            role=self.election_data.candidate_membership_role,
            extra__elected=True
        ):
            constituency_declared.append(membership.post.id)
            total_declared += 1
            constituencies.append((membership.post, True))
        for membership in Membership.objects.select_related('post', 'post__area', 'post__extra').filter(
            post__isnull=False,
            extra__election=self.election_data,
            role=self.election_data.candidate_membership_role
        ).exclude(post_id__in=constituency_declared):
            if constituency_seen.get(membership.post.id, False):
                continue
            constituency_seen[membership.post.id] = True
            constituencies.append((membership.post, False))
        constituencies.sort(key=lambda c: c[0].area.name)
        context['constituencies'] = constituencies
        context['total_constituencies'] = total_constituencies
        context['total_left'] = total_constituencies - total_declared
        context['percent_done'] = (100 * total_declared) // total_constituencies
        return context


class OrderedPartyListView(ElectionMixin, TemplateView):
    template_name = 'candidates/ordered-party-list.html'

    @method_decorator(cache_control(max_age=(60 * 20)))
    def dispatch(self, *args, **kwargs):
        return super(OrderedPartyListView, self).dispatch(
            *args, **kwargs
        )

    def get_context_data(self, **kwargs):
        from ..election_specific import shorten_post_label
        context = super(OrderedPartyListView, self).get_context_data(**kwargs)

        context['post_id'] = post_id = kwargs['post_id']
        post_qs = Post.objects.select_related('extra')
        mp_post = get_object_or_404(post_qs, extra__slug=post_id)

        party_id = kwargs['organization_id']
        party = get_object_or_404(Organization, extra__slug=party_id)

        context['party'] = party

        context['post_label'] = mp_post.label
        context['post_label_shorter'] = shorten_post_label(context['post_label'])

        context['redirect_after_login'] = \
            urlquote(reverse('party-for-post', kwargs={
                'election': self.election,
                'post_id': post_id,
                'organization_id': party_id
            }))

        context['post_data'] = {
            'id': mp_post.extra.slug,
            'label': mp_post.label
        }

        context['candidates_locked'] = mp_post.extra.candidates_locked
        context['lock_form'] = ToggleLockForm(
            initial={
                'post_id': post_id,
                'lock': not context['candidates_locked'],
            },
        )
        context['candidate_list_edits_allowed'] = \
            get_edits_allowed(self.request.user, context['candidates_locked'])

        context['positions_and_people'] = \
            get_party_people_for_election_from_memberships(
                self.election, party.id, mp_post.memberships
            )

        party_set = PartySet.objects.get(postextra__slug=post_id)

        context['add_candidate_form'] = NewPersonForm(
            election=self.election,
            initial={
                ('constituency_' + self.election): post_id,
                ('standing_' + self.election): 'standing',
                ('party_' + party_set.slug + '_' + self.election): party_id,
            },
            hidden_post_widget=True,
        )

        return context
