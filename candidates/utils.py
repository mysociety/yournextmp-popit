from __future__ import unicode_literals

import unicodedata

from compat import bytes_to_unicode

# From http://stackoverflow.com/a/517974/223092
def strip_accents(s):
    return "".join(
        c for c in unicodedata.normalize('NFKD', bytes_to_unicode(s))
        if not unicodedata.combining(c)
    )
