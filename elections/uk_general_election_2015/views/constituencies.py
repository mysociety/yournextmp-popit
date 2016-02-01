from __future__ import unicode_literals

import re

from candidates.utils import strip_accents
from candidates.views import ConstituencyDetailView


def get_electionleaflets_url(mapit_area_id, constituency_name):
    """Generate an electionleaflets.org URL from a constituency name

    >>> (get_electionleaflets_url("66115", "Ynys M\u00F4n") ==
    ...  'http://electionleaflets.org/constituencies/66115/ynys_mon/')
    True
    >>> (get_electionleaflets_url("66056", "Ashton-under-Lyne") ==
    ...  'http://electionleaflets.org/constituencies/66056/ashton_under_lyne/')
    True
    >>> (get_electionleaflets_url("14403", "Ayr, Carrick and Cumnock") ==
    ...  'http://electionleaflets.org/constituencies/14403/ayr_carrick_and_cumnock/')
    True
    """
    result = strip_accents(constituency_name)
    result = result.lower()
    result = re.sub(r'[^a-z]+', ' ', result)
    result = re.sub(r'\s+', ' ', result).strip()
    slug = result.replace(' ', '_')
    url_format = 'http://electionleaflets.org/constituencies/{area_id}/{slug}/'
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
            'https://meetyournextmp.com/linktoseat.html?mapitid={}'.format(
                context['post_id']
            )

        return context
