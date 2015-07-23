import errno
import json
from os.path import dirname, join
import re
import sys
from urlparse import urlsplit

from mock import Mock
from slumber.exceptions import HttpClientError

example_popit_data_directory = join(
    dirname(__file__), '..', 'example-popit-data'
)

def get_example_popit_json(basename):
    with open(
        join(example_popit_data_directory, basename)
    ) as f:
        return json.load(f)

# In many cases we could get away without these fake PopIt API
# collection objects; for example, if you only need to return data on
# one organization in your test, and do a fetch of all people, you
# could do that with:
#
#   In [1]: from mock import Mock
#
#   In [2]: api = Mock(**{
#      ...:     'organizations.return_value.get.return_value': 'got-particular-org',
#      ...:     'persons.get.return_value': 'got-all-people'
#      ...: })
#
#   In [3]: api.organizations('national-assembly').get()
#   Out[3]: 'got-particular-org'
#
#   In [4]: api.organizations.get()
#   Out[4]: <Mock name='mock.organizations.get()' id='140711747445328'>
#
#   In [5]: api.persons.get()
#   Out[5]: 'got-all-people'
#
#   In [6]: api.persons('john-doe').get()
#   Out[6]: <Mock name='mock.persons().get()' id='140711747546640'>
#
# But that would return 'got-particular-org' no matter what ID was
# passed to api.organizations.

class FakeCollection(object):

    # This is the version of get() that's called when invoked on an
    # instance of this class (i.e. to get a single item from a
    # collection)
    def _instance_get(self, **kwargs):
        try:
            return get_example_popit_json(
                '{0}_{1}_embed={2}.json'.format(
                    self.collection,
                    self.object_id,
                    kwargs.get('embed', 'membership')))
        except IOError as e:
            if e.errno == errno.ENOENT:
                raise HttpClientError(
                    'Client Error 404',
                    content='Fake content not found')
            else:
                raise

    def __init__(self, *args):
        self.get = self._instance_get
        self.object_id = args[0] if len(args) == 1 else None

    # This is the version of get() that's called when invoked as a
    # class method (i.e. to get everything in a collection)
    @classmethod
    def get(cls, **kwargs):
        return get_example_popit_json(
            'generic_{0}_embed={1}.json'.format(
                cls.collection,
                kwargs.get('embed', 'membership')
            )
        )

    def delete(self):
        raise Exception("Not implemented: you should patch this")

    def put(self, data):
        raise Exception("Not implemented: you should patch this")

    @staticmethod
    def post(data):
        raise Exception("Not implemented: you should patch this")


class FakePersonCollection(FakeCollection):
    collection = 'persons'

class FakeOrganizationCollection(FakeCollection):
    collection = 'organizations'

class FakePostCollection(FakeCollection):
    collection = 'posts'

class FakeMembershipCollection(FakeCollection):
    collection = 'memberships'


def fake_mp_post_search_results(url, **kwargs):
    mock_requests_response = Mock()
    page = "1"
    m = re.search(r'[^_]page=(\d+)', url)
    if m:
        page = m.group(1)
    mock_requests_response.json.return_value = get_example_popit_json(
        'search_mp_posts_page={0}.json'.format(page)
    )
    return mock_requests_response
