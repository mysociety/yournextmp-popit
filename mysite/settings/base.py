from __future__ import unicode_literals
from os.path import join


from .conf import get_settings

globals().update(get_settings('general.yml'))

# I'm not a big fan of having a local_settings.py file outside version
# control but some partners have asked for this, so this code tries to
# load that file if it's present. (This use Matthew's suggestion for
# allowing local settings overrides with both Python 2 and Python 3;
# this uses exec rather than import so that the local settings can
# modify existing values rather than just overwriting them.)
LOCAL_SETTINGS = join(BASE_DIR, 'mysite', 'settings', 'local_settings.py')
try:
    with open(LOCAL_SETTINGS) as f:
        exec(
            compile(f.read(), 'local_settings.py', 'exec'),
            globals(),
        )
except IOError:
    pass
