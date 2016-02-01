from __future__ import unicode_literals

from datetime import date
from django.conf import settings
from django.contrib.sites.models import Site
from auth_helpers.views import user_in_group
from candidates.models import (
    TRUSTED_TO_MERGE_GROUP_NAME,
    TRUSTED_TO_LOCK_GROUP_NAME,
    TRUSTED_TO_RENAME_GROUP_NAME,
    RESULT_RECORDERS_GROUP_NAME,
)
from moderation_queue.models import QueuedImage, PHOTO_REVIEWERS_GROUP_NAME
from official_documents.models import DOCUMENT_UPLOADERS_GROUP_NAME
from django.utils.translation import to_locale, get_language

SETTINGS_TO_ADD = (
    'ELECTION_APP',
    'GOOGLE_ANALYTICS_ACCOUNT',
    'USE_UNIVERSAL_ANALYTICS',
    'TWITTER_USERNAME',
    'SOURCE_HINTS',
    'MEDIA_URL',
    'SUPPORT_EMAIL',
    'EDITS_ALLOWED',
    'SITE_OWNER',
    'COPYRIGHT_HOLDER',
    'RUNNING_TESTS',
)


def add_settings(request):
    """Add some selected settings values to the context"""

    return {
        'settings': {
            k: getattr(settings, k) for k in SETTINGS_TO_ADD
        }
    }


def election_date(request):
    """Add knowledge of the election date to the context"""

    return {
        'DATE_TODAY': date.today(),
    }


def locale(request):
    """Convert the language string to a locale"""
    """Copied from: http://stackoverflow.com/a/6362929 """
    return {'LOCALE': to_locale(get_language())}


def add_notification_data(request):
    """Make the number of photos for review available in the template"""

    result = {}
    if request.user.is_authenticated():
        result['photos_for_review'] = \
            QueuedImage.objects.filter(decision='undecided').count()
    return result


def add_group_permissions(request):
    """Add user_can_merge and user_can_review_photos"""

    result = {
        context_variable: user_in_group(request.user, group_name)
        for context_variable, group_name in (
            ('user_can_upload_documents', DOCUMENT_UPLOADERS_GROUP_NAME),
            ('user_can_merge', TRUSTED_TO_MERGE_GROUP_NAME),
            ('user_can_review_photos', PHOTO_REVIEWERS_GROUP_NAME),
            ('user_can_lock', TRUSTED_TO_LOCK_GROUP_NAME),
            ('user_can_rename', TRUSTED_TO_RENAME_GROUP_NAME),
            ('user_can_record_results', RESULT_RECORDERS_GROUP_NAME),
        )
    }
    result['user_can_edit'] = settings.EDITS_ALLOWED or request.user.is_staff
    return result

def add_site(request):
    """Make sure the current site is available in all contexts"""

    return {'site': Site.objects.get_current()}
