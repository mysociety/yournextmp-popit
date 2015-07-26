from django.conf import settings
from django.utils.translation import ugettext as _

from auth_helpers.views import user_in_group
from candidates.cache import get_post_cached

TRUSTED_TO_MERGE_GROUP_NAME = 'Trusted To Merge'
TRUSTED_TO_LOCK_GROUP_NAME = 'Trusted To Lock'
TRUSTED_TO_RENAME_GROUP_NAME = 'Trusted To Rename'
RESULT_RECORDERS_GROUP_NAME = 'Result Recorders'

class NameChangeDisallowedException(Exception):
    pass

class ChangeToLockedConstituencyDisallowedException(Exception):
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

def get_constituency_lock(user, api, post_id):
    """Return whether the constituency is locked and whether this user can edit"""

    if not post_id:
        return False, True
    # Use the cached version because it'll be faster than going to
    # PopIt, even if it brings in embeds that we don't need:
    post_data = get_post_cached(api, post_id)['result']
    candidates_locked = bool(post_data.get('candidates_locked'))
    edits_allowed = get_edits_allowed(user, candidates_locked)
    return candidates_locked, edits_allowed

def check_creation_allowed(user, api, new_popit_data):
    for election in settings.ELECTIONS:
        standing_in = new_popit_data['standing_in']
        if election not in standing_in:
            continue
        dummy, edits_allowed = get_constituency_lock(
            user,
            api,
            standing_in[election]['post_id']
        )
        if not edits_allowed:
            raise ChangeToLockedConstituencyDisallowedException(
                _("The candidates for this post are locked now")
            )

def check_update_allowed(user, api, old_popit_data, new_popit_data):
    if settings.RESTRICT_RENAMES:
        allowed_by_group = user_in_group(user, TRUSTED_TO_RENAME_GROUP_NAME)
        name_the_same = old_popit_data['name'] == new_popit_data['name']
        if not (allowed_by_group or name_the_same):
            message = _("Name change from '{0}' to '{1}' by user {2} disallowed")
            raise NameChangeDisallowedException(message.format(
                old_popit_data['name'], new_popit_data['name'], user.username
            ))
    for election in settings.ELECTIONS:
        old_allowed = get_constituency_lock_from_person_data(user, api, election, old_popit_data)[1]
        new_allowed = get_constituency_lock_from_person_data(user, api, election, new_popit_data)[1]
        for (field, key) in [
                ('standing_in', 'post_id'),
                ('party_memberships', 'id')
        ]:
            old_field_value = old_popit_data.get(field, {}) or {}
            new_field_value = new_popit_data.get(field, {}) or {}
            old_post_id = (old_field_value.get(election, {}) or {}).get(key)
            new_post_id = (new_field_value.get(election, {}) or {}).get(key)
            if not (old_allowed and new_allowed) and (old_post_id != new_post_id):
                raise ChangeToLockedConstituencyDisallowedException(
                    _("That update isn't allowed because candidates for a locked "
                    "post would be changed")
                )
