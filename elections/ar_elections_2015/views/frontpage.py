from __future__ import unicode_literals

from candidates.views import AddressFinderView

from cached_counts.models import get_attention_needed_posts

class ArgentineAddressFinder(AddressFinderView):

    country = 'Argentina'

    def get_context_data(self, **kwargs):
        context = super(ArgentineAddressFinder, self).get_context_data(**kwargs)
        context['needing_attention'] = get_attention_needed_posts(5, random=True)
        return context
