from __future__ import unicode_literals

from django.core.urlresolvers import reverse
from django.http import HttpResponseRedirect
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_control
from django.views.decorators.csrf import csrf_exempt
from django.views.generic import FormView

from candidates.views.mixins import ContributorsMixin
from .forms import CantonSelectorForm


class CantonSelectorView(ContributorsMixin, FormView):

    template_name = 'cr/frontpage.html'
    form_class = CantonSelectorForm

    @method_decorator(cache_control(max_age=(60 * 10)))
    @method_decorator(csrf_exempt)
    def dispatch(self, *args, **kwargs):
        return super(CantonSelectorView, self).dispatch(*args, **kwargs)

    def form_valid(self, form):
        area_id = form.cleaned_data['canton_area_id']
        return HttpResponseRedirect(
            reverse('areas-view', kwargs={
                'type_and_area_ids': 'CRCANTON-' + area_id
            })
        )

    def get_context_data(self, **kwargs):
        context = super(CantonSelectorView, self).get_context_data(**kwargs)
        context['top_users'] = self.get_leaderboards()[1]['rows'][:8]
        context['recent_actions'] = self.get_recent_changes_queryset()[:5]
        return context
