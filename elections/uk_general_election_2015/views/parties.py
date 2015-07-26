from candidates.models import get_identifier
from candidates.views import PartyDetailView

class UKPartyDetailView(PartyDetailView):

    def get_context_data(self, **kwargs):
        context = super(UKPartyDetailView, self).get_context_data(**kwargs)

        party_ec_id = get_identifier('electoral-commission', context['party'])
        context['ec_url'] = None
        if party_ec_id:
            ec_tmpl = 'http://search.electoralcommission.org.uk/English/Registrations/{0}'
            context['ec_url'] = ec_tmpl.format(party_ec_id)
        context['register'] = context['party'].get('register')

        return context
