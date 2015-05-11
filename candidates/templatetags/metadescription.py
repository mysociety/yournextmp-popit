from django import template
from datetime import date
from candidates.models import election_date_2005, election_date_2010, election_date_2015
from django.contrib.staticfiles.templatetags.staticfiles import static

register = template.Library()

@register.simple_tag
def metadescription(person, last_cons, today, next_election):
    output = person.name
    if person.last_party:
        if last_cons:
            year_to_check = int(last_cons[0])
        else:
            year_to_check = today.year
        if is_post_election(year_to_check, today, next_election):
            output += " stood "
        else:
            output += " is standing "

        if person.last_party['name'].strip() == "Independent":
            output += "as an independent candidate"
        else:
            party_words = person.last_party['name'].strip().split()
            if party_words[0] != "The":
                output += "for the"
            else:
                output += "for"
            output += " %s" % person.last_party['name']
        if last_cons:
            output += " in %s in %s" % (last_cons[1]['name'], last_cons[0])
    output += " - find out more on YourNextMP"
    return output

def is_post_election(year, today, next_election):
    if year == 2015:
        return today > election_date_2015
    if year == 2010:
        return today > election_date_2010
    if year == 2005:
        return today > election_date_2005
    else:
        return today > next_election

@register.filter
def static_image_path(image_name, request):
    abs_path = static(image_name)
    return request.build_absolute_uri(abs_path)
