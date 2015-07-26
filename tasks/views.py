import json
import requests

from django.views.generic import TemplateView

from candidates.popit import PopItApiMixin, get_search_url
from cached_counts.models import CachedCount

class TaskHomeView(TemplateView):
    template_name = "tasks/tasks_home.html"

class IncompleteFieldView(PopItApiMixin, TemplateView):
    page_kwarg = 'page'
    template_name = 'tasks/field.html'

    def get_template_names(self):
        return [
            'tasks/field_%s.html' % self.kwargs['field'],
            'tasks/field.html'
        ]

    def _objects_from_popit_search(self):
        self.page = int(self.request.GET.get(self.page_kwarg) or 1)
        url = get_search_url(
            'persons',
            "_missing_:%s AND _exists_:standing_in.2015.post_id" %
                self.get_field(),
            page=self.page,
            per_page=20
        )
        page_result = requests.get(url).json()
        return page_result

    def get_context_data(self, **kwargs):
        context = super(IncompleteFieldView,
            self).get_context_data(**kwargs)
        all_results = self._objects_from_popit_search()
        context['results'] = all_results['result']
        context['results_count'] = all_results['total']

        if 'next_url' in all_results.keys():
            context['next'] = self.page + 1
        if 'prev_url' in all_results:
            context['previous'] = self.page -1
        try:
            context['candidates_2015'] = CachedCount.objects.get(
                object_id='candidates_2015').count
            context['percent_empty'] = \
                (100 * context['results_count'] \
                / float(context['candidates_2015']))
        except CachedCount.DoesNotExist:
            pass

        return context

    def get_field(self):
        field = self.kwargs.get('field')
        internal_field = field
        if field == "birth_date":
            internal_field = "versions.data.birth_date"
        if field == "twitter":
            internal_field = "versions.data.twitter_username"
        return internal_field