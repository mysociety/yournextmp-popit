from __future__ import unicode_literals

import errno
import os

# Mimic the behaviour of 'mkdir -p', which just tries to ensure that
# the directory (including any missing parent components of the path)
# exists. This is from http://stackoverflow.com/a/600612/223092

def mkdir_p(path):
    try:
        os.makedirs(path)
    except OSError as e:
        if e.errno == errno.EEXIST and os.path.isdir(path):
            pass
        else:
            raise
