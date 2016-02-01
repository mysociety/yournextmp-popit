from __future__ import unicode_literals

from django.utils.translation import ugettext as _
from django.shortcuts import get_object_or_404

from .models import Election

class ElectionMixin(object):
    '''A mixin to add election data from the URL to the context'''

    def dispatch(self, request, *args, **kwargs):
        self.election = election = self.kwargs['election']
        self.election_data = get_object_or_404(Election, slug=election)
        return super(ElectionMixin, self).dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super(ElectionMixin, self).get_context_data(**kwargs)
        context['election'] = self.election
        context['election_data'] = self.election_data
        return context
