from candidates.views import AddressFinderView

from cached_counts.models import CachedCount

class ArgentineAddressFinder(AddressFinderView):

    country = 'Argentina'

    def get_context_data(self, **kwargs):
        context = super(ArgentineAddressFinder, self).get_context_data(**kwargs)
        context['needing_attention'] = \
            CachedCount.get_attention_needed_queryset()[:5]
        return context
