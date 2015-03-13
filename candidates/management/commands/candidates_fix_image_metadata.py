from PIL import Image
from hashlib import md5
import re
import requests
import sys
from StringIO import StringIO

from candidates.popit import PopItApiMixin, popit_unwrap_pagination
from candidates.update import fix_dates
from moderation_queue.views import PILLOW_FORMAT_MIME_TYPES

from django.core.management.base import BaseCommand

from slumber.exceptions import HttpClientError

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
        for person in popit_unwrap_pagination(
                self.api.persons,
                per_page=100
        ):
            msg = "Person {0}persons/{1}"
            print msg.format(self.get_base_url(), person['id'])
            for image in person.get('images', []):
                print "  Image with URL:", image['url']
                fix_image(image)
                image.pop('_id', None)
                # Some images have an empty 'created' field, which
                # causes an Elasticsearch indexing error, so remove
                # that if it's the case:
                if not image.get('created'):
                    image.pop('created', None)
            fix_dates(person)
            try:
                self.api.persons(person['id']).put(person)
            except HttpClientError as e:
                print "HttpClientError", e.content
                sys.exit(1)
