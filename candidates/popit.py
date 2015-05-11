from copy import deepcopy
from urlparse import urlunsplit

from django.conf import settings
from django.utils.http import urlquote

from popit_api import PopIt

def create_popit_api_object():
    api_properties = {
        'instance': settings.POPIT_INSTANCE,
        'hostname': settings.POPIT_HOSTNAME,
        'port': settings.POPIT_PORT,
        'api_version': 'v0.1',
        'append_slash': False,
    }
    if settings.POPIT_API_KEY:
        api_properties['api_key'] = settings.POPIT_API_KEY
    else:
        api_properties['user'] = settings.POPIT_USER
        api_properties['password'] = settings.POPIT_PASSWORD
    return PopIt(**api_properties)

def popit_unwrap_pagination(api_collection, **kwargs):
    page = 1
    keep_fetching = True
    while keep_fetching:
        get_kwargs = {
            'per_page': 50,
            'page': page,
        }
        get_kwargs.update(kwargs)
        response = api_collection.get(**get_kwargs)
        keep_fetching = response.get('has_more', False)
        page += 1
        for api_object in response['result']:
            yield api_object

def merge_popit_dicts(primary, secondary):
    result = {}
    for key in set(primary.keys() + secondary.keys()):
        if primary.get(key) and not secondary.get(key):
            result[key] = primary[key]
        elif secondary.get(key) and not primary.get(key):
            result[key] = secondary[key]
        elif key in primary:
            result[key] = primary[key]
        else:
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


class PopItApiMixin(object):

    """This provides helper methods for manipulating data in a PopIt instance"""

    def __init__(self, *args, **kwargs):
        super(PopItApiMixin, self).__init__(*args, **kwargs)
        self.api = create_popit_api_object()

    def get_base_url(self):
        port = settings.POPIT_PORT
        instance_hostname = settings.POPIT_INSTANCE + \
            '.' + settings.POPIT_HOSTNAME
        if port != 80:
            instance_hostname += ':' + str(port)
        base_url = urlunsplit(
            ('http', instance_hostname, '/api/v0.1/', '', '')
        )
        return base_url

    def get_search_url(self, collection, query, **kwargs):
        base_search_url = self.get_base_url() + 'search/'
        parameters = {
            'q': query,
        }
        parameters.update(kwargs)
        query_string = '&'.join(
            k + '=' + urlquote(v) for k, v in parameters.items()
        )
        return base_search_url + collection + '?' + query_string
