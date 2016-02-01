from __future__ import unicode_literals

from django.views.generic import FormView
from django.http import HttpResponseRedirect
from django.utils.http import urlquote
from django.utils.six.moves.urllib_parse import urlparse

from ..forms import UserTermsAgreementForm


class AskForCopyrightAssigment(FormView):

    form_class = UserTermsAgreementForm
    template_name = 'candidates/ask-for-copyright-assignment.html'

    def get_initial(self):
        initial = super(AskForCopyrightAssigment, self).get_initial().copy()
        next_url = self.request.GET['next']
        parsed_url = urlparse(next_url)
        initial['next_path'] = parsed_url.path
        return initial

    def form_valid(self, form):
        ta = self.request.user.terms_agreement
        ta.assigned_to_dc = True
        ta.save()
        return HttpResponseRedirect(form.cleaned_data['next_path'])

    def get_context_data(self, **kwargs):
        context = super(AskForCopyrightAssigment, self) \
            .get_context_data(**kwargs)
        context['next_path_escaped'] = urlquote(self.request.GET['next'])
        return context
