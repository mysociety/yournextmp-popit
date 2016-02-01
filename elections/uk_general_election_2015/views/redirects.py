from __future__ import unicode_literals

from django.views.generic import RedirectView


class ConstituenciesRedirect(RedirectView):

    permanent = True

    def get_redirect_url(self, *args, **kwargs):
        return '/election/2015/constituencies' + kwargs['list_filter']


class ConstituencyRedirect(RedirectView):

    permanent = True

    def get_redirect_url(self, *args, **kwargs):
        return '/election/2015/post/' + kwargs['rest_of_path']


class PartyRedirect(RedirectView):

    permanent = True

    def get_redirect_url(self, *args, **kwargs):
        return '/election/2015/part' + kwargs['rest_of_path']


class CandidacyRedirect(RedirectView):

    permanent = True

    def get_redirect_url(self, *args, **kwargs):
        return '/election/2015/candidacy' + kwargs['rest_of_path']


class PersonCreateRedirect(RedirectView):

    permanent = True

    def get_redirect_url(self, *args, **kwargs):
        return '/election/2015/person/create/'


class CachedCountsRedirect(RedirectView):

    permanent = True

    def get_redirect_url(self, *args, **kwargs):
        if kwargs['rest_of_path'] == 'constituencies':
            new_rest_of_path = 'posts'
        else:
            new_rest_of_path = 'parties'
        return '/numbers/election/2015/' + new_rest_of_path

class OfficialDocumentsRedirect(RedirectView):

    permanent = True

    def get_redirect_url(self, *args, **kwargs):
        return '/upload_document/upload/election/2015/post/' + kwargs['rest_of_path']
