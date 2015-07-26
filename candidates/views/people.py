import re

from slugify import slugify

from django.conf import settings
from django.contrib import messages
from django.core.urlresolvers import reverse
from django.http import (
    HttpResponseRedirect, HttpResponsePermanentRedirect
)
from django.utils.decorators import method_decorator
from django.utils.http import urlquote
from django.utils.translation import ugettext as _
from django.views.decorators.cache import cache_control
from django.views.generic import FormView, TemplateView, View

from braces.views import LoginRequiredMixin

from auth_helpers.views import GroupRequiredMixin, user_in_group
from elections.mixins import ElectionMixin

from ..diffs import get_version_diffs
from ..election_specific import PARTY_DATA
from .version_data import get_client_ip, get_change_metadata
from ..forms import NewPersonForm, UpdatePersonForm
from ..models import (
    LoggedAction, PersonRedirect,
    TRUSTED_TO_MERGE_GROUP_NAME,
    PopItPerson
)
from ..popit import (
    merge_popit_people, PopItApiMixin, get_base_url
)

def get_flash_message(person, new_person=False):
    if new_person:
        prompt_intro = _('Thank-you for adding <a href="{person_url}">{person_name}</a>!')
    else:
        prompt_intro = _('Thank-you for updating <a href="{person_url}">{person_name}</a>!')

    prompt_intro+= _(' Now you can carry on to:')

    format_kwargs = {
        'person_url': reverse('person-view', kwargs={'person_id': person.id}),
        'person_edit_url': reverse('person-update', kwargs={'person_id': person.id}),
        'person_name': person.name,
        'needing_attention_url': reverse('attention_needed'),
    }

    election_li = _(
        '<li><a href="{person_create_url}">Add another '
        'candidate in the {election_name}</a></li>'
    )
    same_post_again = '\n'.join(
        election_li.format(
            person_create_url=reverse(
                'person-create', kwargs={'election': election}
            ),
            election_name=election_data['name']
        )
        for election, election_data in settings.ELECTIONS_CURRENT
        if person.standing_in.get(election)
    )

    return (
        prompt_intro + \
        '<ul>' + \
        _('<li><a href="{person_edit_url}">Edit {person_name} '
          'again</a></li>') + \
        _('<li>Add a candidate for <a href="{needing_attention_url}">one of '
          'the posts with fewest candidates</a></li>') + \
        same_post_again + \
        '</ul>'
    ).format(**format_kwargs)


class PersonView(PopItApiMixin, TemplateView):
    template_name = 'candidates/person-view.html'

    @method_decorator(cache_control(max_age=(60 * 20)))
    def dispatch(self, *args, **kwargs):
        return super(PersonView, self).dispatch(
            *args, **kwargs
        )

    def get_context_data(self, **kwargs):
        context = super(PersonView, self).get_context_data(**kwargs)
        context['popit_api_url'] = get_base_url()
        path = self.person.get_absolute_url()
        context['redirect_after_login'] = urlquote(path)
        context['canonical_url'] = self.request.build_absolute_uri(path)
        context['person'] = self.person
        context['last_election'] = self.person.last_cons
        if self.person.last_cons:
            context['constituency'] = self.person.last_cons[1]['name']
            context['contested_election'] = self.person.last_cons[0]
        else:
            context['constituency'] = ''
            context['contested_election'] = ''
        return context

    def get(self, request, *args, **kwargs):
        self.person = PopItPerson.create_from_popit(
            self.api,
            self.kwargs['person_id']
        )
        # If there's a PersonRedirect for this person ID, do the
        # redirect, otherwise process the GET request as usual.
        try:
            new_person_id = PersonRedirect.objects.get(
                old_person_id=self.person.id
            ).new_person_id
            return HttpResponsePermanentRedirect(
                reverse('person-view', kwargs={
                    'person_id': new_person_id,
                    'ignored_slug': self.person.get_slug(),
                })
            )
        except PersonRedirect.DoesNotExist:
            return super(PersonView, self).get(request, *args, **kwargs)


class RevertPersonView(LoginRequiredMixin, PopItApiMixin, View):

    http_method_names = [u'post']

    def post(self, request, *args, **kwargs):
        version_id = self.request.POST['version_id']
        person_id = self.kwargs['person_id']
        source = self.request.POST['source']

        person = PopItPerson.create_from_popit(
            self.api,
            self.kwargs['person_id']
        )

        data_to_revert_to = None
        for version in person.versions:
            if version['version_id'] == version_id:
                data_to_revert_to = version['data']
                break

        if not data_to_revert_to:
            message = _("Couldn't find the version {0} of person {1}")
            raise Exception(message.format(version_id, person_id))

        change_metadata = get_change_metadata(self.request, source)
        person.update_from_reduced_json(data_to_revert_to)
        person.record_version(change_metadata)
        person.save_to_popit(self.api, self.request.user)

        # Log that that action has taken place, and will be shown in
        # the recent changes, leaderboards, etc.
        LoggedAction.objects.create(
            user=self.request.user,
            action_type='person-revert',
            ip_address=get_client_ip(self.request),
            popit_person_new_version=change_metadata['version_id'],
            popit_person_id=person_id,
            source=change_metadata['information_source'],
        )

        return HttpResponseRedirect(
            reverse(
                'person-view',
                kwargs={'person_id': person_id}
            )
        )

class MergePeopleView(GroupRequiredMixin, PopItApiMixin, View):

    http_method_names = [u'post']
    required_group_name = TRUSTED_TO_MERGE_GROUP_NAME

    def post(self, request, *args, **kwargs):
        # Check that the person IDs are well-formed:
        primary_person_id = self.kwargs['person_id']
        secondary_person_id = self.request.POST['other']
        if not re.search('^\d+$', secondary_person_id):
            message = _("Malformed person ID '{0}'")
            raise ValueError(message.format(secondary_person_id))
        if primary_person_id == secondary_person_id:
            message = _("You can't merge a person ({0}) with themself ({1})")
            raise ValueError(message.format(
                primary_person_id, secondary_person_id
            ))
        primary_person, secondary_person = [
            PopItPerson.create_from_popit(self.api, popit_id)
            for popit_id in (primary_person_id, secondary_person_id)
        ]
        # Merge them (which will include a merged versions array):
        merged_person = merge_popit_people(
            primary_person.as_reduced_json(),
            secondary_person.as_reduced_json(),
        )
        # Update the primary person in PopIt:
        change_metadata = get_change_metadata(
            self.request, _('After merging person {0}').format(secondary_person_id)
        )
        primary_person.update_from_reduced_json(merged_person)
        primary_person.record_version(change_metadata)
        primary_person.save_to_popit(self.api, self.request.user)
        # Now we delete the old person:
        self.api.persons(secondary_person_id).delete()
        # Create a redirect from the old person to the new person:
        PersonRedirect.objects.create(
            old_person_id=secondary_person_id,
            new_person_id=primary_person_id,
        )
        # Log that that action has taken place, and will be shown in
        # the recent changes, leaderboards, etc.
        LoggedAction.objects.create(
            user=self.request.user,
            action_type='person-merge',
            ip_address=get_client_ip(self.request),
            popit_person_new_version=change_metadata['version_id'],
            popit_person_id=primary_person_id,
            source=change_metadata['information_source'],
        )
        # And redirect to the primary person with the merged data:
        return HttpResponseRedirect(
            reverse('person-view', kwargs={
                'person_id': primary_person_id,
                'ignored_slug': slugify(primary_person.name),
            })
        )

class UpdatePersonView(LoginRequiredMixin, PopItApiMixin, FormView):
    template_name = 'candidates/person-edit.html'
    form_class = UpdatePersonForm

    def get_initial(self):
        initial_data = super(UpdatePersonView, self).get_initial()
        person = PopItPerson.create_from_popit(
            self.api, self.kwargs['person_id']
        )
        initial_data.update(person.get_initial_form_data())
        return initial_data

    def get_context_data(self, **kwargs):
        context = super(UpdatePersonView, self).get_context_data(**kwargs)

        person = PopItPerson.create_from_popit(
            self.api,
            self.kwargs['person_id']
        )
        context['person'] = person

        context['user_can_merge'] = user_in_group(
            self.request.user,
            TRUSTED_TO_MERGE_GROUP_NAME
        )

        context['versions'] = get_version_diffs(person.versions)

        context['constituencies_form_fields'] = []
        for election, election_data in settings.ELECTIONS_BY_DATE:
            if not election_data.get('current'):
                continue
            context['constituencies_form_fields'].append(
                {
                    'election_name': election_data['name'],
                    'standing': kwargs['form']['standing_' + election],
                    'constituency': kwargs['form']['constituency_' + election],
                    'party_fields': [
                        kwargs['form']['party_' + p['slug'] + '_' + election]
                        for p in PARTY_DATA.ALL_PARTY_SETS
                    ]
                }
            )

        return context

    def form_valid(self, form):

        if not (settings.EDITS_ALLOWED or self.request.user.is_staff):
            return HttpResponseRedirect(reverse('all-edits-disallowed'))

        # First parse that person's data from PopIt into our more
        # usable data structure:

        person = PopItPerson.create_from_popit(
            self.api, self.kwargs['person_id']
        )

        # Now we need to make any changes to that data structure based
        # on information given in the form.

        change_metadata = get_change_metadata(
            self.request, form.cleaned_data.pop('source')
        )

        person.update_from_form(self.api, form)

        LoggedAction.objects.create(
            user=self.request.user,
            action_type='person-update',
            ip_address=get_client_ip(self.request),
            popit_person_new_version=change_metadata['version_id'],
            popit_person_id=person.id,
            source=change_metadata['information_source'],
        )

        person.record_version(change_metadata)
        person.save_to_popit(self.api, self.request.user)

        # Add a message to be displayed after redirect:
        messages.add_message(
            self.request,
            messages.SUCCESS,
            get_flash_message(person, new_person=False),
            extra_tags='safe do-something-else'
        )

        return HttpResponseRedirect(reverse('person-view', kwargs={'person_id': person.id}))


class NewPersonView(ElectionMixin, LoginRequiredMixin, PopItApiMixin, FormView):
    template_name = 'candidates/person-create.html'
    form_class = NewPersonForm

    def get_form_kwargs(self):
        kwargs = super(NewPersonView, self).get_form_kwargs()
        kwargs['election'] = self.election
        return kwargs

    def get_initial(self):
        result = super(NewPersonView, self).get_initial()
        result['standing_' + self.election] = 'standing'
        return result

    def form_valid(self, form):

        if not (settings.EDITS_ALLOWED or self.request.user.is_staff):
            return HttpResponseRedirect(reverse('all-edits-disallowed'))

        person = PopItPerson()
        person.update_from_form(self.api, form)
        change_metadata = get_change_metadata(
            self.request, form.cleaned_data['source']
        )
        person.record_version(change_metadata)
        action = LoggedAction.objects.create(
            user=self.request.user,
            action_type='person-create',
            ip_address=get_client_ip(self.request),
            popit_person_new_version=change_metadata['version_id'],
            source=change_metadata['information_source'],
        )
        person_id = person.save_to_popit(self.api, self.request.user)
        action.popit_person_id = person_id
        action.save()

        # Add a message to be displayed after redirect:
        messages.add_message(
            self.request,
            messages.SUCCESS,
            get_flash_message(person, new_person=True),
            extra_tags='safe do-something-else'
        )

        return HttpResponseRedirect(reverse('person-view', kwargs={'person_id': person_id}))
