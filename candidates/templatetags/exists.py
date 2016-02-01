from __future__ import unicode_literals

import json

from django import template

register = template.Library()

@register.filter(name='exists')
def exists(value):
    return bool(value)
