import re

from django import template
from django.conf import settings
from django.contrib.sites.models import Site
from django.contrib.staticfiles.templatetags.staticfiles import static
from django.utils.translation import ugettext as _
from django.utils.translation import get_language

register = template.Library()

@register.simple_tag
def metadescription(person, last_cons, today):
    if person.last_party:
        last_party_name = format_party_name(person.last_party['name'])
        args = {
            'election': last_cons[0],
            'name': person.name,
            'party': last_party_name,
            'post': last_cons[1]['name'],
        }
        if is_post_election(last_cons[0], today):
            if last_party_name == _("Independent") % args:
                output = _("%(name)s stood as an independent candidate in %(post)s in %(election)s") % args
            else:
                output = _("%(name)s stood for %(party)s in %(post)s in %(election)s") % args
        else:
            if last_party_name == _("Independent") % args:
                output = _("%(name)s is standing as an independent candidate in %(post)s in %(election)s")
            else:
                output = _("%(name)s is standing for %(party)s in %(post)s in %(election)s") % args
    else:
        output = person.name

    output += " - " + _("find out more on {site_name}").format(
        site_name=Site.objects.get_current().name
    )
    return output

def is_post_election(election, today):
    return today > settings.ELECTIONS[election]['election_date']

def format_party_name(party_name):
    party_name = party_name.strip()
    if get_language()[0:2] == "en":
        # otherwise we end up with "the Independent", which sounds like
        # they're standing for a newspaper
        if party_name != "Independent":
            party_name = re.sub('^The ', 'the ', party_name)
            party_words = party_name.split()
            if party_words[0] != "the":
                return "the %s" % party_name
    return party_name

@register.filter
def static_image_path(image_name, request):
    abs_path = static(image_name)
    return request.build_absolute_uri(abs_path)
