from django.core.urlresolvers import reverse
from django.http import HttpResponseRedirect
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_control
from django.views.decorators.csrf import csrf_exempt
from django.views.generic import FormView
from django.conf import settings

from candidates.models.address import check_address
from .mixins import ContributorsMixin

from ..forms import AddressForm

class AddressFinderView(ContributorsMixin, FormView):
    template_name = 'candidates/frontpage.html'
    form_class = AddressForm
    country = None

    @method_decorator(cache_control(max_age=(60 * 10)))
    @method_decorator(csrf_exempt)
    def dispatch(self, *args, **kwargs):
        return super(AddressFinderView, self).dispatch(*args, **kwargs)

    def form_valid(self, form):
        form.cleaned_data['address']
        resolved_address = check_address(
            form.cleaned_data['address'],
            country=self.country,
        )
        return HttpResponseRedirect(
            reverse('areas-view', kwargs=resolved_address)
        )

    def get_context_data(self, **kwargs):
        context = super(AddressFinderView, self).get_context_data(**kwargs)
        context['top_users'] = self.get_leaderboards()[1]['rows'][:8]
        context['recent_actions'] = self.get_recent_changes_queryset()[:5]
        context['election_data'] = settings.ELECTIONS_CURRENT[-1][1]
        return context
