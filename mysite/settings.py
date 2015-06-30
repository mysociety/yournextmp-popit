"""
Django settings for mysite project.

For more information on this file, see
https://docs.djangoproject.com/en/1.6/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/1.6/ref/settings/
"""

# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
from django.conf.global_settings import TEMPLATE_CONTEXT_PROCESSORS, LANGUAGES
from django.utils.translation import to_locale, ugettext_lazy as _
import importlib
import os
import re
import sys
import yaml
BASE_DIR = os.path.dirname(os.path.dirname(__file__))

from .helpers import mkdir_p

configuration_file_basename = 'general.yml'
# All the test data is specific to the UK, so if we seem to be running
# tests, use the general.yml-example (which has UK settings):
if 'test' in sys.argv:
    configuration_file_basename = 'general.yml-example'

configuration_file = os.path.join(
    BASE_DIR, 'conf', configuration_file_basename
)

with open(configuration_file) as f:
    conf = yaml.load(f)

ALLOWED_HOSTS = conf.get('ALLOWED_HOSTS')

# Load the credentials for the PopIt instance

POPIT_INSTANCE = conf['POPIT_INSTANCE']
POPIT_HOSTNAME = conf['POPIT_HOSTNAME']
POPIT_PORT = conf.get('POPIT_PORT', 80)
POPIT_USER = conf.get('POPIT_USER', '')
POPIT_PASSWORD = conf.get('POPIT_PASSWORD', '')
POPIT_API_KEY = conf.get('POPIT_API_KEY', '')

GOOGLE_ANALYTICS_ACCOUNT = conf.get('GOOGLE_ANALYTICS_ACCOUNT')

# The email address which is made public on the site for sending
# support email to:
SUPPORT_EMAIL = conf['SUPPORT_EMAIL']

# Email addresses that error emails are sent to when DEBUG = False
ADMINS = conf['ADMINS']

# The From: address for all emails except error emails
DEFAULT_FROM_EMAIL = conf['DEFAULT_FROM_EMAIL']

# The From: address for error emails
SERVER_EMAIL = conf['SERVER_EMAIL']

# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/1.6/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = conf['SECRET_KEY']

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = bool(int(conf.get('STAGING')))

TEMPLATE_DEBUG = True

TEMPLATE_DIRS = (
    os.path.join(BASE_DIR, 'mysite', 'templates'),
)

TEMPLATE_CONTEXT_PROCESSORS += (
    # Required by allauth template tags
    "django.core.context_processors.request",
    # allauth specific context processors
    "allauth.account.context_processors.account",
    "allauth.socialaccount.context_processors.socialaccount",
    "django.contrib.messages.context_processors.messages",
    "mysite.context_processors.add_settings",
    "mysite.context_processors.election_date",
    "mysite.context_processors.add_group_permissions",
    "mysite.context_processors.add_notification_data",
    "mysite.context_processors.locale",
)

ELECTION_APP = conf['ELECTION_APP']
ELECTION_APP_FULLY_QUALIFIED = 'elections.' + ELECTION_APP

# Application definition

INSTALLED_APPS = (
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.humanize',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.sites',
    'django_nose',
    'pipeline',
    ELECTION_APP_FULLY_QUALIFIED,
    'candidates',
    'tasks',
    'cached_counts',
    'moderation_queue',
    'auth_helpers',
    'debug_toolbar',
    'template_timings_panel',
    'official_documents',
    'results',
    'allauth',
    'allauth.account',
    'allauth.socialaccount',
    'allauth.socialaccount.providers.google',
    'allauth.socialaccount.providers.facebook',
    'allauth.socialaccount.providers.twitter',
)

SITE_ID = 1

MIDDLEWARE_CLASSES = (
    'debug_toolbar.middleware.DebugToolbarMiddleware',
    'candidates.middleware.PopItDownMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.locale.LocaleMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'candidates.middleware.CopyrightAssignmentMiddleware',
    'candidates.middleware.DisallowedUpdateMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
)

AUTHENTICATION_BACKENDS = (
    # Needed to login by username in Django admin, regardless of `allauth`
    "django.contrib.auth.backends.ModelBackend",
    # `allauth` specific authentication methods, such as login by e-mail
    "allauth.account.auth_backends.AuthenticationBackend",
)

SOCIALACCOUNT_PROVIDERS = {
    'google': {'SCOPE': ['https://www.googleapis.com/auth/userinfo.profile'],
               'AUTH_PARAMS': {'access_type': 'online'}},
    'facebook': {'SCOPE': ['email',]},
}

LOGIN_REDIRECT_URL = '/'

ACCOUNT_EMAIL_VERIFICATION = "mandatory"
ACCOUNT_EMAIL_REQUIRED = True
ACCOUNT_USERNAME_REQUIRED = True
SOCIALACCOUNT_AUTO_SIGNUP = True
if not conf.get('NEW_ACCOUNTS_ALLOWED', True):
    ACCOUNT_ADAPTER = 'mysite.account_adapter.NoNewUsersAccountAdapter'

ROOT_URLCONF = 'mysite.urls'

WSGI_APPLICATION = 'mysite.wsgi.application'

DEBUG_TOOLBAR_PATCH_SETTINGS = False

DEBUG_TOOLBAR_PANELS = [
    'debug_toolbar.panels.versions.VersionsPanel',
    'debug_toolbar.panels.timer.TimerPanel',
    'debug_toolbar.panels.settings.SettingsPanel',
    'debug_toolbar.panels.headers.HeadersPanel',
    'debug_toolbar.panels.request.RequestPanel',
    'debug_toolbar.panels.sql.SQLPanel',
    'debug_toolbar.panels.staticfiles.StaticFilesPanel',
    'debug_toolbar.panels.templates.TemplatesPanel',
    'debug_toolbar.panels.cache.CachePanel',
    'debug_toolbar.panels.signals.SignalsPanel',
    'debug_toolbar.panels.logging.LoggingPanel',
    'debug_toolbar.panels.redirects.RedirectsPanel',
    'template_timings_panel.panels.TemplateTimings.TemplateTimings',
]

INTERNAL_IPS = ['127.0.0.1']

# Database
# https://docs.djangoproject.com/en/1.6/ref/settings/#databases

if conf.get('DATABASE_SYSTEM') == 'postgresql':
    DATABASES = {
        'default': {
            'ENGINE':   'django.db.backends.postgresql_psycopg2',
            'NAME':     conf.get('YNMP_DB_NAME'),
            'USER':     conf.get('YNMP_DB_USER'),
            'PASSWORD': conf.get('YNMP_DB_PASS'),
            'HOST':     conf.get('YNMP_DB_HOST'),
            'PORT':     conf.get('YNMP_DB_PORT'),
        }
    }
else:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': os.path.join(BASE_DIR, 'db.sqlite3'),
        }
    }

# Internationalization
# https://docs.djangoproject.com/en/1.6/topics/i18n/

LOCALE_PATHS = [
    os.path.join(BASE_DIR, 'locale')
]

LANGUAGES = [l for l in LANGUAGES if os.path.exists(os.path.join(LOCALE_PATHS[0], to_locale(l[0])))]
LANGUAGE_CODE = conf.get('LANGUAGE_CODE', 'en-gb')

TIME_ZONE = conf.get('TIME_ZONE', 'Europe/London')

USE_I18N = True

USE_L10N = True

USE_TZ = True

MEDIA_ROOT = conf.get('MEDIA_ROOT')
if not MEDIA_ROOT:
    MEDIA_ROOT = os.path.join(BASE_DIR, 'media')
# Make sure that the MEDIA_ROOT and subdirectory for archived CSV
# files exist:
mkdir_p(os.path.join(MEDIA_ROOT, 'csv-archives'))

MEDIA_URL = '/media/'

# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/1.6/howto/static-files/

STATIC_URL = '/static/'

STATIC_ROOT = os.path.join(BASE_DIR, 'static')

if 'test' not in sys.argv:
    STATICFILES_STORAGE = 'pipeline.storage.PipelineCachedStorage'

STATICFILES_DIRS = (
    os.path.join(BASE_DIR, 'mysite/static'),
)

STATICFILES_FINDERS = (
    'django.contrib.staticfiles.finders.FileSystemFinder',
    'django.contrib.staticfiles.finders.AppDirectoriesFinder',
    'pipeline.finders.PipelineFinder',
)

PIPELINE_CSS = {
    'image-review': {
        'source_filenames': (
            'moderation_queue/css/jquery.Jcrop.css',
            'moderation_queue/css/crop.scss',
            'moderation_queue/css/photo-upload.scss',
        ),
        'output_filename': 'css/image-review.css',
    },
    'official_documents': {
        'source_filenames': (
            'official_documents/css/official_documents.scss',
        ),
        'output_filename': 'css/official_documents.css',
    },
    'all': {
        'source_filenames': (
            'candidates/style.scss',
            'cached_counts/style.scss',
            'select2/select2.css',
            'jquery/jquery-ui.css',
            'jquery/jquery-ui.structure.css',
            'jquery/jquery-ui.theme.css',
        ),
        'output_filename': 'css/all.css',
    }
}

PIPELINE_JS = {
    'image-review': {
        'source_filenames': (
            'moderation_queue/js/jquery.color.js',
            'moderation_queue/js/jquery.Jcrop.js',
            'moderation_queue/js/crop.js',
        ),
        'output_filename': 'js/image-review.js',
    },
    'all': {
        'source_filenames': (
            'jquery/jquery-1.11.1.js',
            'jquery/jquery-ui.js',
            'foundation/js/foundation/foundation.js',
            'foundation/js/foundation/foundation.equalizer.js',
            'foundation/js/foundation/foundation.dropdown.js',
            'foundation/js/foundation/foundation.tooltip.js',
            'foundation/js/foundation/foundation.offcanvas.js',
            'foundation/js/foundation/foundation.accordion.js',
            'foundation/js/foundation/foundation.joyride.js',
            'foundation/js/foundation/foundation.alert.js',
            'foundation/js/foundation/foundation.topbar.js',
            'foundation/js/foundation/foundation.reveal.js',
            'foundation/js/foundation/foundation.slider.js',
            'foundation/js/foundation/foundation.magellan.js',
            'foundation/js/foundation/foundation.clearing.js',
            'foundation/js/foundation/foundation.orbit.js',
            'foundation/js/foundation/foundation.interchange.js',
            'foundation/js/foundation/foundation.abide.js',
            'foundation/js/foundation/foundation.tab.js',
            'select2/select2.js',
            'js/post-to-party-set.js',
            'js/constituency.js',
            'js/person_form.js',
            'js/versions.js',
        ),
        'output_filename': 'js/all.js'
    }
}

PIPELINE_COMPILERS = (
  'pipeline.compilers.sass.SASSCompiler',
)

PIPELINE_CSS_COMPRESSOR = 'pipeline.compressors.yui.YUICompressor'
PIPELINE_JS_COMPRESSOR = 'pipeline.compressors.yui.YUICompressor'

# On some platforms this might be called "yuicompressor", so it may be
# necessary to symlink it into your PATH as "yui-compressor".
PIPELINE_YUI_BINARY = '/usr/bin/env yui-compressor'

TEST_RUNNER = 'django_nose.NoseTestSuiteRunner'

SOUTH_TESTS_MIGRATE = False

NOSE_ARGS = [
    '--nocapture',
    '--with-doctest',
    '--with-yanc',
    # There are problems with OpenCV on Travis, so don't even try to
    # import moderation_queue/faces.py
    '--ignore-files=faces',
]

SOURCE_HINTS = _(u'''Please don't quote third-party candidate sites \u2014
we prefer URLs of news stories or official candidate pages.''')

# By default, cache successful results from MapIt for a day
MAPIT_CACHE_SECONDS = 86400

FORCE_HTTPS_IMAGES = conf.get('FORCE_HTTPS_IMAGES')

if conf.get('NGINX_SSL'):
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
    ACCOUNT_DEFAULT_HTTP_PROTOCOL = 'https'

if DEBUG:
    cache = {'BACKEND': 'django.core.cache.backends.dummy.DummyCache'}
else:
    cache = {
        'TIMEOUT': None, # cache keys never expire; we invalidate them
        'BACKEND': 'django.core.cache.backends.memcached.MemcachedCache',
        'LOCATION': '127.0.0.1:11211',
        'KEY_PREFIX': DATABASES['default']['NAME'],
    }

CACHES = {
    'default': cache
}

RESTRICT_RENAMES = conf.get('RESTRICT_RENAMES')

EDITS_ALLOWED = conf.get('EDITS_ALLOWED', True)

# Import any settings from the election application's settings module:
ELECTION_SETTINGS_MODULE = ELECTION_APP_FULLY_QUALIFIED + '.settings'
elections_module = importlib.import_module(ELECTION_SETTINGS_MODULE)

ELECTIONS = elections_module.ELECTIONS

ELECTIONS_BY_DATE = sorted(
    ELECTIONS.items(),
    key=lambda e: (e[1]['election_date'], e[0]),
)

ELECTION_RE = '(?P<election>'
ELECTION_RE += '|'.join(
    re.escape(t[0]) for t in ELECTIONS_BY_DATE
)
ELECTION_RE += ')'

ELECTIONS_CURRENT = [t for t in ELECTIONS_BY_DATE if t[1].get('current')]

# FIXME: we should never really need "an arbitrary current election";
# this is just here for the moment because we don't have a page for
# "all elections for this point" yet (i.e. area pages) - places where
# this is used in the code are effectively FIXMEs too.
ARBITRARY_CURRENT_ELECTION = ELECTIONS_CURRENT[-1] if ELECTIONS_CURRENT else None

# Make sure there's a trailing slash at the end of base MapIt URL:
MAPIT_BASE_URL = re.sub(r'/*$', '/', elections_module.MAPIT_BASE_URL)

MAPIT_TYPES = set()
for e in ELECTIONS_CURRENT:
    for mapit_type in e[1]['mapit_types']:
        MAPIT_TYPES.add(mapit_type)

KNOWN_MAPIT_GENERATIONS = set(
    e[1]['mapit_generation'] for e in ELECTIONS_CURRENT
)
if len(KNOWN_MAPIT_GENERATIONS) > 1:
    message = "More than one MapIt generation for current elections: {0}"
    raise Exception(message.format(KNOWN_MAPIT_GENERATIONS))

MAPIT_CURRENT_GENERATION = list(KNOWN_MAPIT_GENERATIONS)[0]

MAPIT_TYPES_GENERATIONS_ELECTIONS = {
    (mapit_type, t[1]['mapit_generation']): t
    for t in ELECTIONS_CURRENT
    for mapit_type in t[1]['mapit_types']
}
