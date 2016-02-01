from __future__ import unicode_literals

from django.db.models import Prefetch
from django.views.generic import TemplateView

from candidates.models import PostExtra
from elections.models import Election

class PostListView(TemplateView):
    template_name = 'candidates/posts.html'

    def get_context_data(self, **kwargs):
        context = super(PostListView, self).get_context_data(**kwargs)

        prefetch_qs = \
            PostExtra.objects.order_by('base__label').select_related('base')

        context['all_posts'] = \
            [
                {
                    'election': election,
                    'posts': election.posts.all()
                }
                for election in
                Election.objects.current().order_by('-election_date'). \
                    prefetch_related(
                        Prefetch('posts', queryset=prefetch_qs)
                    )
            ]
        return context
