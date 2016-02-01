from __future__ import unicode_literals

from candidates.views import PartyDetailView
from popolo.models import Identifier

class UKPartyDetailView(PartyDetailView):

    def get_context_data(self, **kwargs):
        context = super(UKPartyDetailView, self).get_context_data(**kwargs)

        context['ec_url'] = ''
        context['register'] = ''
        try:
            party_ec_id = context['party'].identifiers.get(scheme='electoral-commission')
            if party_ec_id:
                ec_tmpl = 'http://search.electoralcommission.org.uk/English/Registrations/{0}'
                context['ec_url'] = ec_tmpl.format(party_ec_id)
            context['register'] = context['party'].extra.register
        except Identifier.DoesNotExist:
            pass

        return context
