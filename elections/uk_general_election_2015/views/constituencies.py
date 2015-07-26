import re

from candidates.utils import strip_accents
from candidates.views import ConstituencyDetailView


def get_electionleaflets_url(mapit_area_id, constituency_name):
    """Generate an electionleaflets.org URL from a constituency name

    >>> get_electionleaflets_url(u"66115", u"Ynys M\u00F4n")
    u'http://electionleaflets.org/constituencies/66115/ynys_mon/'
    >>> get_electionleaflets_url(u"66056", u"Ashton-under-Lyne")
    u'http://electionleaflets.org/constituencies/66056/ashton_under_lyne/'
    >>> get_electionleaflets_url(u"14403", u"Ayr, Carrick and Cumnock")
    u'http://electionleaflets.org/constituencies/14403/ayr_carrick_and_cumnock/'
    """
    result = strip_accents(constituency_name)
    result = result.lower()
    result = re.sub(r'[^a-z]+', ' ', result)
    result = re.sub(r'\s+', ' ', result).strip()
    slug = result.replace(' ', '_')
    url_format = u'http://electionleaflets.org/constituencies/{area_id}/{slug}/'
    return url_format.format(area_id=mapit_area_id, slug=slug)


class UKConstituencyDetailView(ConstituencyDetailView):

    template_name = 'uk_general_election_2015/constituency.html'

    def get_context_data(self, **kwargs):
        context = super(UKConstituencyDetailView, self).get_context_data(**kwargs)

        context['electionleaflets_url'] = \
            get_electionleaflets_url(
                context['post_id'],
                context['post_label_shorter']
            )

        context['meetyournextmp_url'] = \
            u'https://meetyournextmp.com/linktoseat.html?mapitid={}'.format(
                context['post_id']
            )

        return context
