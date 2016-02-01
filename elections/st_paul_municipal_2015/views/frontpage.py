from __future__ import unicode_literals

from django.http import HttpResponseRedirect
from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.core.urlresolvers import reverse
from django.utils.translation import ugettext as _

from candidates.views import AddressFinderView
from candidates.forms import AddressForm

from pygeocoder import Geocoder, GeocoderError
import requests

from elections.st_paul_municipal_2015.settings import OCD_BOUNDARIES_URL

class StPaulAddressForm(AddressForm):

    def clean_address(self):
        address = self.cleaned_data['address']
        check_address(address)
        return address

class StPaulAddressFinder(AddressFinderView):

    form_class = StPaulAddressForm
    country = 'United States'

    def form_valid(self, form):
        form.cleaned_data['address']
        resolved_address = check_address(
            form.cleaned_data['address'],
            country=self.country,
        )
        return HttpResponseRedirect(
            reverse('st-paul-areas-view', kwargs=resolved_address)
        )


def get_cached_boundary(division_id):
    if cache.get(division_id):
        return cache.get(division_id)

    boundary = requests.get('{0}/boundaries/'.format(OCD_BOUNDARIES_URL),
                            params={'external_id': division_id})
    cache.set(division_id, boundary.json(), None)

    return boundary.json()

def check_address(address_string, country=None):
    tidied_address = address_string.strip()

    if country is not None:
        tidied_address += ', ' + country

    try:
        location_results = Geocoder.geocode(tidied_address)
    except GeocoderError:
        message = _("Failed to find a location for '{0}'")
        raise ValidationError(message.format(tidied_address))

    coords = ','.join([str(p) for p in location_results[0].coordinates])

    if cache.get(coords):
        return {'coords': coords}

    boundaries = requests.get('{0}/boundaries'.format(OCD_BOUNDARIES_URL),
                              params={'contains': coords})

    if boundaries.json()['meta']['total_count'] > 0:

        areas = set()

        for area in boundaries.json()['objects']:
            division_slug = area['external_id'].replace('/', ',')
            if cache.get(area['external_id']):
                areas.add(division_slug)
            elif not 'precinct' in division_slug:
                cache.set(area['external_id'], area, None)
                areas.add(division_slug)

        return {
            'area_ids': ';'.join(sorted(areas)),
        }

    error = _("Unable to find constituency for '{0}'")
    raise ValidationError(error.format(tidied_address))
