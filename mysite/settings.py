"""
Django settings for mysite project.

For more information on this file, see
https://docs.djangoproject.com/en/1.6/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/1.6/ref/settings/
"""

# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
from django.conf.global_settings import TEMPLATE_CONTEXT_PROCESSORS
import os
import sys
import yaml
BASE_DIR = os.path.dirname(os.path.dirname(__file__))

from .helpers import mkdir_p

configuration_file = os.path.join(
    BASE_DIR, 'conf', 'general.yml'
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
)

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
    'allauth',
    'allauth.account',
    'allauth.socialaccount',
    'allauth.socialaccount.providers.google',
    'allauth.socialaccount.providers.facebook',
    'allauth.socialaccount.providers.twitter',
    'pipeline',
    'candidates',
    'tasks',
    'cached_counts',
    'moderation_queue',
    'auth_helpers',
    'debug_toolbar',
    'official_documents',
    'results',
)

SITE_ID = 1

MIDDLEWARE_CLASSES = (
    'debug_toolbar.middleware.DebugToolbarMiddleware',
    'candidates.middleware.PopItDownMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
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

LANGUAGE_CODE = 'en-gb'

TIME_ZONE = 'Europe/London'

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
            'js/mapit-areas-ni.js',
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

SOURCE_HINTS = u'''Please don't quote third-party candidate sites \u2014
we prefer URLs of news stories or official candidate pages.'''

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
