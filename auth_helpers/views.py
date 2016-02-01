from __future__ import unicode_literals

from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import Group
from django.shortcuts import render
from django.utils.decorators import method_decorator


def user_in_group(user, group_name):
    if not user.is_authenticated():
        return False
    group = Group.objects.get(name=group_name)
    return group in user.groups.all()


class GroupRequiredMixin(object):

    """A mixin that requires the user is a member of a particular group

    You should set 'required_group_name' on the class that uses this
    mixin to the name of the group that the user must be a member of."""

    permission_denied_template = 'auth_helpers/group_permission_denied.html'

    @method_decorator(login_required)
    def dispatch(self, request, *args, **kwargs):
        if not user_in_group(request.user, self.required_group_name):
            return render(request, self.permission_denied_template, status=403)
        return super(GroupRequiredMixin, self).dispatch(
            request, *args, **kwargs
        )
