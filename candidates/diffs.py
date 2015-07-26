# The functions in this file are to help produce human readable diffs
# between our JSON representation of candidates.

import re

from django.conf import settings
from django.utils.translation import ugettext as _

import jsonpatch
import jsonpointer



def get_descriptive_value(election, attribute, value, leaf):
    """Get a sentence fragment describing someone's status in a particular year

    'attribute' is either "standing_in" or "party_membership", 'election'
    is one of the keys from settings.ELECTIONS, and 'value' is what would
    be under that year in the 'standing_in' or 'party_memberships'
    dictionary (see the comment at the top of update.py)."""

    election_data = settings.ELECTIONS[election]
    current_election = election_data.get('current')
    election_name = election_data['name']

    if attribute == 'party_memberships':
        if leaf:
            # In that case, there's only a particular value in the
            # dictionary that's changed:
            if leaf == 'name':
                if current_election:
                    message = _(u"is known to be standing for the party '{party}' in the {election}")
                else:
                    message = _(u"was known to be standing for the party '{party}' in the {election}")
                return message.format(party=value, election=election_name)
            elif leaf == 'id':
                if current_election:
                    message = _(u'is known to be standing for the party with ID {party} in the {election}')
                else:
                    message = _(u'was known to be standing for the party with ID {party} in the {election}')
                return message.format(party=value, election=election_name)
            else:
                message = _(u"Unexpected leaf {0} (attribute: {1}, election: {2}")
                raise Exception, message.format(
                    leaf, attribute, election
                )
        else:
            if current_election:
                message = _(u'is known to be standing for the party "{party}" in the {election}')
            else:
                message = _(u'was known to be standing for the party "{party}" in the {election}')
            return message.format(party=value['name'], election=election_name)
    elif attribute == 'standing_in':
        if value is None:
            if current_election:
                message = _(u'is known not to be standing in the {election}')
            else:
                message = _(u'was known not to be standing in the {election}')
            return message.format(election=election_name)
        else:
            if leaf:
                if leaf == 'post_id':
                    if current_election:
                        message = _("is known to be standing for the post with ID {party} in the {election}")
                    else:
                        message = _("was known to be standing for the post with ID {party} in the {election}")
                    return message.format(party=value, election=election_name)
                elif leaf == 'mapit_url':
                    if current_election:
                        message = _("is known to be standing in the constituency with MapIt URL {party} in the {election}")
                    else:
                        message = _("was known to be standing in the constituency with MapIt URL {party} in the {election}")
                    return message.format(party=value, election=election_name)
                elif leaf == 'name':
                    if current_election:
                        message = _("is known to be standing in {party} in the {election}")
                    else:
                        message = _("was known to be standing in {party} in the {election}")
                    return message.format(party=value, election=election_name)
                elif leaf == 'elected':
                    if value:
                        return _("was elected in the {election}").format(election=election_name)
                    else:
                        return _("was not elected in the {election}").format(election=election_name)
                else:
                    message = _(u"Unexpected leaf {0} (attribute: {1}, election: {2}")
                    raise Exception, message.format(
                        leaf, attribute, election
                    )
            else:
                if current_election:
                    message = _(u'is known to be standing in {party} in the {election}')
                else:
                    message = _(u'was known to be standing in {party} in the {election}')
                return message.format(party=value['name'], election=election_name)

def explain_standing_in_and_party_memberships(operation, attribute, election, leaf):
    """Set 'value' and 'previous_value' in operation to a readable explanation

    'attribute' is one of 'standing_in' or 'party_memberships'."""

    for key in ('previous_value', 'value'):
        if key not in operation:
            continue
        if election:
            operation[key] = get_descriptive_value(
                election,
                attribute,
                operation[key],
                leaf,
            )
        else:
            clauses = []
            for election, value in (operation[key] or {}).items():
                clauses.append(get_descriptive_value(
                    election,
                    attribute,
                    value,
                    leaf,
                ))
            operation[key] = _(u' and ').join(clauses)

def get_version_diff(from_data, to_data):
    """Calculate the diff (a mangled JSON patch) between from_data and to_data"""

    basic_patch = jsonpatch.make_patch(from_data, to_data)
    result = []
    for operation in basic_patch:
        op = operation['op']
        # We deal with standing_in and party_memberships slightly
        # differently so they can be presented in human-readable form,
        # so match those cases first:
        m = re.search(
            r'(standing_in|party_memberships)(?:/([-_A-Za-z0-9]+))?(?:/(\w+))?',
            operation['path'],
        )
        if op in ('replace', 'remove'):
            operation['previous_value'] = \
                jsonpointer.resolve_pointer(
                    from_data,
                    operation['path']
                )
        attribute, election, leaf = m.groups() if m else (None, None, None)
        if attribute:
            explain_standing_in_and_party_memberships(operation, attribute, election, leaf)
        if op in ('replace', 'remove'):
            # Ignore replacing no data with no data:
            if op == 'replace' and \
               not operation['previous_value'] and \
               not operation['value']:
                continue
            if op == 'replace' and not operation['previous_value']:
                operation['op'] = 'add'
        elif op == 'add':
            # It's important that we don't skip the case where a
            # standing_in value is being set to None, because that's
            # saying 'we *know* they're not standing then'
            if (not operation['value']) and (attribute != 'standing_in'):
                continue
        operation['path'] = re.sub(r'^/', '', operation['path'])
        result.append(operation)
    result.sort(key=lambda o: (o['op'], o['path']))
    return result

def clean_version_data(data):
    # We're not interested in changes of these IDs:
    for i in data.get('identifiers', []):
        i.pop('id', None)
    for on in data.get('other_names', []):
        on.pop('id', None)
    data.pop('last_party', None)
    data.pop('proxy_image', None)
    data.pop('date_of_birth', None)

def get_version_diffs(versions):
    """Add a diff to each of an array of version dicts

    The first version is the most recent; the last is the original
    version."""

    result = []
    n = len(versions)
    for i, v in enumerate(versions):
        # to_version_data = replace_empty_with_none(
        #     versions[i]['data']
        # )
        to_version_data = versions[i]['data']
        if i == (n - 1):
            from_version_data = {}
        else:
            # from_version_data = replace_empty_with_none(
            #     versions[i + 1]['data']
            # )
            from_version_data = versions[i + 1]['data']
        clean_version_data(to_version_data)
        clean_version_data(from_version_data)
        version_with_diff = versions[i].copy()
        version_with_diff['diff'] = \
            get_version_diff(from_version_data, to_version_data)
        result.append(version_with_diff)
    return result
