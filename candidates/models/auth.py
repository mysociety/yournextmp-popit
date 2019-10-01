from __future__ import unicode_literals

from contextlib import contextmanager

from django.conf import settings
from django.utils.translation import ugettext as _

from usersettings.shortcuts import get_current_usersettings
from auth_helpers.views import user_in_group
from popolo.models import Person

TRUSTED_TO_MERGE_GROUP_NAME = 'Trusted To Merge'
TRUSTED_TO_LOCK_GROUP_NAME = 'Trusted To Lock'
TRUSTED_TO_RENAME_GROUP_NAME = 'Trusted To Rename'
TRUSTED_TO_MARK_FOR_REVIEW_GROUP_NAME = 'Trusted To Mark For Review'
RESULT_RECORDERS_GROUP_NAME = 'Result Recorders'
EDIT_SETTINGS_GROUP_NAME = 'Can Edit Settings'

class NameChangeDisallowedException(Exception):
    pass

class ChangeToLockedConstituencyDisallowedException(Exception):
    pass

class UnauthorizedAttemptToChangeMarkedForReview(Exception):
    pass

def get_constituency_lock_from_person_data(user, api, election, person_popit_data):
    """Return whether the constituency is locked and whether this user can edit"""

    standing_in = person_popit_data.get('standing_in', {}) or {}
    standing_in_election = standing_in.get(election, {}) or {}
    return get_constituency_lock(
        user,
        api,
        standing_in_election.get('post_id')
    )

def get_edits_allowed(user, candidates_locked):
    return user.is_authenticated() and (
        user_in_group(user, TRUSTED_TO_LOCK_GROUP_NAME) or
        (not candidates_locked)
    )

def get_constituency_lock(user, post):
    """Return whether the constituency is locked and whether this user can edit

    You should make sure that 'extra' is populated on the post that's
    passed in to avoid an extra query."""

    if post is None:
        return False, True
    # Use the cached version because it'll be faster than going to
    # PopIt, even if it brings in embeds that we don't need:
    candidates_locked = post.extra.candidates_locked
    edits_allowed = get_edits_allowed(user, candidates_locked)
    return candidates_locked, edits_allowed

def check_creation_allowed(user, new_candidacies):
    for candidacy in new_candidacies:
        post = candidacy.post
        dummy, edits_allowed = get_constituency_lock(user, post)
        if not edits_allowed:
            raise ChangeToLockedConstituencyDisallowedException(
                _("The candidates for this post are locked now")
            )

@contextmanager
def check_update_allowed(user, person):
    old_name = person.name
    person_extra = person.extra
    old_candidacies = person_extra.current_candidacies
    old_marked_for_review = person_extra.marked_for_review
    yield
    # Refetch the person from the database so we don't get cached
    # data:
    new_person = Person.objects.get(pk=person.pk)
    new_person_extra = new_person.extra
    new_name = new_person.name
    new_candidacies = new_person_extra.current_candidacies
    new_marked_for_review = new_person_extra.marked_for_review
    check_update_allowed_inner(
        user,
        old_name, old_candidacies, old_marked_for_review,
        new_name, new_candidacies, new_marked_for_review,
    )

def check_update_allowed_inner(
        user,
        old_name, old_candidacies, old_marked_for_review,
        new_name, new_candidacies, new_marked_for_review):
    # Check whether an unauthorized user has tried to rename someone
    # while RESTRICT_RENAMES is set:
    usersettings = get_current_usersettings()
    if usersettings.RESTRICT_RENAMES:
        allowed_by_group = user_in_group(user, TRUSTED_TO_RENAME_GROUP_NAME)
        name_the_same = old_name == new_name
        if not (allowed_by_group or name_the_same):
            message = _("Name change from '{0}' to '{1}' by user {2} disallowed")
            raise NameChangeDisallowedException(message.format(
                old_name, new_name, user.username
            ))
    # Check that none of the posts that the person's leaving or
    # joining were locked:
    old_posts = set(c.post for c in old_candidacies)
    new_posts = set(c.post for c in new_candidacies)
    for post in old_posts ^ new_posts:
        dummy, edits_allowed = get_constituency_lock(user, post)
        if not edits_allowed:
            raise ChangeToLockedConstituencyDisallowedException(
                _("That update isn't allowed because candidates for a locked "
                  "post ({post_label}) would be changed").format(
                      post_label=post.label
                  )
            )
    # Now check that if they're changing the "marked for review" flag,
    # that the user is in the required group:
    if old_marked_for_review != new_marked_for_review:
        if not user_in_group(user, TRUSTED_TO_MARK_FOR_REVIEW_GROUP_NAME):
            msg = 'Unauthorized user {0} tried to change marked_for_review'
            raise UnauthorizedAttemptToChangeMarkedForReview(msg.format(user))
    # Now check that they're not changing party in a locked
    # constituency:
    for post in old_posts & new_posts:
        old_party = next(c.on_behalf_of for c in old_candidacies if c.post == post)
        new_party = next(c.on_behalf_of for c in new_candidacies if c.post == post)
        dummy, edits_allowed = get_constituency_lock(user, post)
        if not edits_allowed and (old_party != new_party):
            raise ChangeToLockedConstituencyDisallowedException(
                _("That update isn't allowed because you can't change the party "
                  "(in this case from {old_party} to {new_party}) for a candidate "
                  "in a locked post ({post_label})").format(
                      old_party=old_party.name, new_party=new_party.name,
                      post_label=post.label
                  )
            )
