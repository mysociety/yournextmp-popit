# If you need to define any views specific to this country's site, put
# those definitions here.

from __future__ import unicode_literals

from django.core.urlresolvers import reverse
from django.http import HttpResponseRedirect
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_control
from django.views.decorators.csrf import csrf_exempt
from django.views.generic import FormView

from slugify import slugify

from popolo.models import Post
from candidates.views.mixins import ContributorsMixin
from .forms import CountySelectorForm


class CountySelectorView(ContributorsMixin, FormView):

    template_name = 'kenya/frontpage.html'
    form_class = CountySelectorForm

    @method_decorator(cache_control(max_age=(60 * 10)))
    @method_decorator(csrf_exempt)
    def dispatch(self, *args, **kwargs):
        return super(CountySelectorView, self).dispatch(*args, **kwargs)

    """
    We know there is only one election and one post for each area so
    hard code those assumptions to reduce clicks
    """
    def form_valid(self, form):
        area = form.cleaned_data['county_id']
        return HttpResponseRedirect(
            reverse('areas-view', kwargs={
                'type_and_area_ids': 'CTR-country:1,DIS-' + area.identifier
            })
        )

    def get_context_data(self, **kwargs):
        context = super(CountySelectorView, self).get_context_data(**kwargs)
        return context
