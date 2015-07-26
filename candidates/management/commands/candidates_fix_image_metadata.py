from PIL import Image
from hashlib import md5
import re
import requests
import sys
from StringIO import StringIO

from candidates.models import fix_dates, PopItPerson
from candidates.popit import (
    PopItApiMixin, popit_unwrap_pagination, get_base_url
)

from django.core.management.base import BaseCommand

from slumber.exceptions import HttpClientError

PILLOW_FORMAT_MIME_TYPES = {
    'JPEG': 'image/jpeg',
    'PNG': 'image/png',
    'GIF': 'image/gif',
}

def fix_image_mime_type(image):
    mime_type = image.get('mime_type')
    if mime_type:
        return
    try:
        image_url = image['url']
        r = requests.get(image_url)
        pillow_image = Image.open(StringIO(r.content))
    except IOError as e:
        if 'cannot identify image file' in unicode(e):
            print "Unknown image format in {0}".format(image_url)
            return
        raise
    new_mime_type = PILLOW_FORMAT_MIME_TYPES[pillow_image.format]
    image['mime_type'] = new_mime_type
    print "    Setting mime_type to", new_mime_type

def fix_image_metadata(image):
    notes = image.get('notes', '')
    # If the notes field has an MD5sum in it, then it was from the
    # import PPC script, so move that to an md5sum field (as
    # organization images have) and set the moderator_why_allowed to
    # 'profile-photo'
    m = re.search(r'^md5sum:([a-f0-9]+)', notes)
    if m:
        image['md5sum'] = m.group(1)
        image['moderator_why_allowed'] = 'profile-photo'
        image['notes'] = 'Scraped from the official party PPC page'
        print "    Migrated old PPC scraped image"
    # If there is a 'why_allowed' and 'justification_for_use' field,
    # this was from before we switched to separating the user's and
    # moderator's reason for allowing the photo, so migrate those
    # fields.
    if image.get('why_allowed') and image.get('justification_for_use'):
        why_allowed = image.pop('why_allowed')
        justification_for_use = image.pop('justification_for_use')
        image['moderator_why_allowed'] = why_allowed
        image['user_why_allowed'] = why_allowed
        image['user_justification_for_use'] = justification_for_use
        print "    Migrated from old why_allowed", why_allowed
        print "    Migrated from old justification_for_use", justification_for_use

def ensure_md5sum_present(image):
    if image.get('md5sum'):
        return
    image_url = image['url']
    # Otherwise get the file and calculate its MD5sum
    r = requests.get(image_url)
    md5sum = md5(r.content).hexdigest()
    image['md5sum'] = md5sum
    print "    Setting md5sum field to", md5sum

def fix_image(image):
    fix_image_mime_type(image)
    fix_image_metadata(image)
    ensure_md5sum_present(image)


class Command(PopItApiMixin, BaseCommand):

    def handle(self, **options):
        for collection in ('organization', 'person'):
            api_collection = getattr(self.api, collection + 's')
            message = "{titled} {base_url}{plural}/{id}"
            for item in popit_unwrap_pagination(
                    api_collection,
                    embed='',
                    per_page=100
            ):
                print message.format(
                    titled=collection.title(),
                    base_url=get_base_url(),
                    plural=(collection + "s"),
                    id=item['id']
                )
                for image in item.get('images', []):
                    print "  Image with URL:", image['url']
                    fix_image(image)
                    # Some images have an empty 'created' field, which
                    # causes an Elasticsearch indexing error, so change it
                    # to null if that's the case:
                    if not image.get('created'):
                        image['created'] = None
                fix_dates(item)
                try:
                    api_collection(item['id']).put(item)
                except HttpClientError as e:
                    print "HttpClientError", e.content
                    sys.exit(1)
                # If this is a person, make sure that the
                # corresponding cache entries are invalidated:
                if collection == 'person':
                    person = PopItPerson.create_from_dict(item)
                    person.invalidate_cache_entries()
