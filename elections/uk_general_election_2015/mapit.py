# coding=utf-8

import re

import requests

from django.conf import settings
from django.core.cache import cache
from django.utils.http import urlquote
from django.utils.translation import ugettext as _

from candidates.mapit import (
    BaseMapItException, BadPostcodeException, UnknownMapitException
)


class NoConstituencyForPostcodeException(BaseMapItException):
    pass


def get_wmc_from_postcode(original_postcode):
    postcode = re.sub(r'(?ms)\s*', '', original_postcode.lower())
    if re.search(r'[^a-z0-9]', postcode):
        raise BadPostcodeException(
            _(u'There were disallowed characters in "{0}"').format(original_postcode)
        )
    cached_result = cache.get(postcode)
    if cached_result:
        return cached_result
    url = 'http://mapit.mysociety.org/postcode/' + urlquote(postcode)
    r = requests.get(url)
    if r.status_code == 200:
        mapit_result = r.json()
        wmc = mapit_result.get('shortcuts', {}).get('WMC')
        if not wmc:
            raise NoConstituencyForPostcodeException(
                _(u'No constituency found for the postcode "{0}"').format(
                    original_postcode
                )
            )
        cache.set(postcode, wmc, settings.MAPIT_CACHE_SECONDS)
        return wmc
    elif r.status_code == 400:
        mapit_result = r.json()
        raise BadPostcodeException(mapit_result['error'])
    elif r.status_code == 404:
        raise BadPostcodeException(
            _(u'The postcode “{0}” couldn’t be found').format(original_postcode)
        )
    else:
        raise UnknownMapitException(
            _(u'Unknown MapIt error for postcode "{0}"').format(
                original_postcode
            )
        )
