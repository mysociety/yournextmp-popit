from __future__ import unicode_literals

from copy import deepcopy


def merge_popit_dicts(primary, secondary):
    result = deepcopy(primary)
    for key in secondary:
        if not primary.get(key):
            result[key] = secondary[key]
    return result


def merge_popit_arrays(primary_array, secondary_array):
    # This isn't very efficient, but unlike the more efficient:
    #    return primary_array + list(set(secondary_array) - set(primary_array))
    # ... the following works even if elements of the list are
    # unhashable (e.g. dicts):
    return primary_array + [e for e in secondary_array if e not in primary_array]


def merge_popit_people(primary, secondary):
    result = deepcopy(secondary)
    for primary_key, primary_value in primary.items():
        # If there's no value in primary, don't write that over
        # whatever's in the secondary:
        if not primary_value:
            continue
        secondary_value = result.get(primary_key)
        if primary_key == 'name' and secondary_value:
            if primary_value != secondary_value:
                # Then the names conflict; add the secondary name to
                # 'other_names' to preserve it.
                other_names = result.get('other_names', [])
                other_names.append({'name': secondary_value})
                result['other_names'] = other_names
        if isinstance(primary_value, list) and isinstance(secondary_value, list):
            result[primary_key] = merge_popit_arrays(primary_value, secondary_value)
        elif isinstance(primary_value, dict) and isinstance(secondary_value, dict):
            result[primary_key] = merge_popit_dicts(primary_value, secondary_value)
        else:
            result[primary_key] = primary_value
    return result
