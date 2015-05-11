# The functions in this file are to help produce human readable diffs
# between our JSON representation of candidates.

import re

import jsonpatch
import jsonpointer

def get_descriptive_value(year, attribute, value, leaf):
    """Get a sentence fragmetn describing someone's status in a particular year

    'attribute' is either "standing_in" or "party_membership", 'year'
    is either "2010" or "2015", and 'value' is what would be under
    that year in the 'standing_in' or 'party_memberships' dictionary
    (see the comment at the top of update.py)."""

    prefix = {'2010': u'was', '2015': u'is'}[year]
    if attribute == 'party_memberships':
        if leaf:
            # In that case, there's only a particular value in the
            # dictionary that's changed:
            if leaf == 'name':
                message = u"{0} known to be standing for the party '{1}' in {2}"
                return message.format(prefix, value, year)
            elif leaf == 'id':
                message = u'{0} known to be standing for the party with ID {1} in {2}'
                return message.format(prefix, value, year)
            else:
                message = u"Unexpected leaf {0} (attribute: {1}, year: {2}"
                raise Exception, message.format(
                    leaf, attribute, year
                )
        else:
            message = u'{0} known to be standing for the party "{1}" in {2}'
            return message.format(prefix, value['name'], year)
    elif attribute == 'standing_in':
        if value is None:
            message = u'{0} known not to be standing in {1}'
            return message.format(prefix, year)
        else:
            if leaf:
                if leaf == 'post_id':
                    message = "{0} known to be standing for the post with ID {1} in {2}"
                    return message.format(prefix, value, year)
                elif leaf == 'mapit_url':
                    message = "{0} known to be standing in the constituency with MapIt URL {1} in {2}"
                    return message.format(prefix, value, year)
                elif leaf == 'name':
                    message = "{0} known to be standing in {1} in {2}"
                    return message.format(prefix, value, year)
                elif leaf == 'elected':
                    return "was {whether}elected in {year}".format(
                        whether=('' if value else 'not '),
                        year=year
                    )
                else:
                    message = u"Unexpected leaf {0} (attribute: {1}, year: {2}"
                    raise Exception, message.format(
                        leaf, attribute, year
                    )
            else:
                message = u'{0} known to be standing in {1} in {2}'
                return message.format(prefix, value['name'], year)

def explain_standing_in_and_party_memberships(operation, attribute, year, leaf):
    """Set 'value' and 'previous_value' in operation to a readable explanation

    'attribute' is one of 'standing_in' or 'party_memberships'."""

    for key in ('previous_value', 'value'):
        if key not in operation:
            continue
        if year:
            operation[key] = get_descriptive_value(
                year,
                attribute,
                operation[key],
                leaf,
            )
        else:
            clauses = []
            for year, value in (operation[key] or {}).items():
                clauses.append(get_descriptive_value(
                    year,
                    attribute,
                    value,
                    leaf,
                ))
            operation[key] = ' and '.join(clauses)

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
            r'(standing_in|party_memberships)(?:/(201[05]))?(?:/(\w+))?',
            operation['path'],
        )
        if op in ('replace', 'remove'):
            operation['previous_value'] = \
                jsonpointer.resolve_pointer(
                    from_data,
                    operation['path']
                )
        attribute, year, leaf = m.groups() if m else (None, None, None)
        if attribute:
            explain_standing_in_and_party_memberships(operation, attribute, year, leaf)
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
