from __future__ import unicode_literals

import json

from django import template

register = template.Library()

@register.filter(name='prettyjson')
def prettyjson(value):
    return json.dumps(value, indent=4, sort_keys=True, ensure_ascii=False)
