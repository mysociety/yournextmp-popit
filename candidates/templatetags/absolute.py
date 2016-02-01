from __future__ import unicode_literals

from django import template
from django.contrib.staticfiles.templatetags.staticfiles import static

register = template.Library()

@register.filter
def absolute_url(abs_path, request):
    return request.build_absolute_uri(abs_path)

@register.filter
def static_image_path(image_name, request):
    abs_path = static(image_name)
    return absolute_url(abs_path, request)
