from django.conf import settings
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_control
from django.views.decorators.csrf import csrf_exempt
from django.views.generic import FormView

from candidates.cache import get_post_cached
from candidates.popit import PopItApiMixin
from candidates.views.helpers import get_redirect_to_post
from candidates.views.mixins import ContributorsMixin

from ..forms import (PostcodeForm, ConstituencyForm)
from ..mapit import get_wmc_from_postcode


def get_current_election():
    current_elections = [t[0] for t in settings.ELECTIONS_CURRENT]
    if len(current_elections) != 1:
        message = "There should be exactly one current election in " + \
            "uk_general_election_2015, not {0}"
        raise Exception(message.format(len(current_elections)))
    return current_elections[0]


class ConstituencyPostcodeFinderView(ContributorsMixin, PopItApiMixin, FormView):
    template_name = 'candidates/finder.html'
    form_class = PostcodeForm

    @method_decorator(cache_control(max_age=(60 * 10)))
    @method_decorator(csrf_exempt)
    def dispatch(self, *args, **kwargs):
        return super(ConstituencyPostcodeFinderView, self).dispatch(*args, **kwargs)

    def form_valid(self, form):
        wmc = get_wmc_from_postcode(form.cleaned_data['postcode'])
        post_data = get_post_cached(self.api, wmc)['result']
        return get_redirect_to_post(get_current_election(), post_data)

    def get_context_data(self, **kwargs):
        context = super(ConstituencyPostcodeFinderView, self).get_context_data(**kwargs)
        context['postcode_form'] = kwargs.get('form') or PostcodeForm()
        context['constituency_form'] = ConstituencyForm()
        context['show_postcode_form'] = True
        context['show_name_form'] = False
        context['top_users'] = self.get_leaderboards()[1]['rows'][:8]
        context['recent_actions'] = self.get_recent_changes_queryset()[:5]
        context['election_data'] = settings.ELECTIONS_CURRENT[-1][1]
        return context


class ConstituencyNameFinderView(ContributorsMixin, PopItApiMixin, FormView):
    template_name = 'candidates/finder.html'
    form_class = ConstituencyForm

    @method_decorator(cache_control(max_age=(60 * 10)))
    @method_decorator(csrf_exempt)
    def dispatch(self, *args, **kwargs):
        return super(ConstituencyNameFinderView, self).dispatch(*args, **kwargs)

    def form_valid(self, form):
        post_id = form.cleaned_data['constituency']
        post_data = get_post_cached(self.api, post_id)['result']
        return get_redirect_to_post(get_current_election(), post_data)

    def get_context_data(self, **kwargs):
        context = super(ConstituencyNameFinderView, self).get_context_data(**kwargs)
        context['postcode_form'] = PostcodeForm()
        context['constituency_form'] = kwargs.get('form') or ConstituencyForm()
        context['show_postcode_form'] = False
        context['show_name_form'] = True
        context['top_users'] = self.get_leaderboards()[1]['rows'][:8]
        context['recent_actions'] = self.get_recent_changes_queryset()[:5]
        context['election_data'] = settings.ELECTIONS_CURRENT[-1][1]
        return context
