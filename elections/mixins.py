from django.conf import settings
from django.http import Http404
from django.utils.translation import ugettext as _


class ElectionMixin(object):
    '''A mixin to add election data from the URL to the context'''

    def dispatch(self, request, *args, **kwargs):
        self.election = election = self.kwargs['election']
        if election not in settings.ELECTIONS:
            raise Http404(_("Unknown election: '{election}'").format(election=election))
        self.election_data = settings.ELECTIONS[election]
        return super(ElectionMixin, self).dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super(ElectionMixin, self).get_context_data(**kwargs)
        context['election'] = self.election
        context['election_data'] = self.election_data
        return context
