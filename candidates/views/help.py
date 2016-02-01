from __future__ import unicode_literals

from django.core.urlresolvers import reverse
from django.views.generic import TemplateView

from elections.models import Election

class HelpApiView(TemplateView):
    template_name = 'candidates/api.html'

    def get_context_data(self, **kwargs):
        context = super(HelpApiView, self).get_context_data(**kwargs)

        context['current_csv_list'] = []
        for election_data in Election.objects.current().by_date():
            context['current_csv_list'].append({'slug': election_data.slug, 'name': election_data.name})

        context['historic_csv_list'] = []
        current_slugs = [election['slug'] for election in context['current_csv_list']]
        for election_data in Election.objects.by_date():
            if election_data.slug not in current_slugs:
                context['historic_csv_list'].append(
                    {'slug': election_data.slug, 'name': election_data.name})

        context['base_api_url'] = self.request.build_absolute_uri(
            reverse('api-root', kwargs={'version': 'v0.9'})
        )
        return context


class HelpAboutView(TemplateView):
    template_name = 'candidates/about.html'
