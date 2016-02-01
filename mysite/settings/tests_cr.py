from __future__ import unicode_literals

from .conf import get_settings

globals().update(
    get_settings(
        'general.yml-example',
        election_app='cr',
        tests=True,
    ),
)

NOSE_ARGS += ['-a', 'country=cr']
