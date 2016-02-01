#!/usr/bin/env python
from __future__ import unicode_literals

import os
import sys

from django.core.management import CommandParser

# It's nice if "./manage.py test" works out-of-the-box, so work out if
# "test" is the subcommand and the user hasn't specified a settings
# module with --settings.  If so, use the settings module for
# non-country-specific tests that we know has the right INSTALLED_APPS
# and tests are expected to pass with. This won't help confusion if
# someone uses "django-admin.py test" instead, but it's some help...
# (Note that if someone's set the DJANGO_SETTINGS_MODULE environment
# variable, this default won't be used either.)

try:
    subcommand = sys.argv[1]
except IndexError:
    subcommand = 'help'

parser = CommandParser(None)
parser.add_argument('--settings')
try:
    options, args = parser.parse_known_args(sys.argv[2:])
except:
    # Ignore any errors at this point; the arguments will be parsed
    # again shortly anyway.
    args = []

run_default_tests = (subcommand == 'test' and not options.settings)

if __name__ == "__main__":

    if run_default_tests:
        settings_module = 'mysite.settings.tests'
    else:
        settings_module = 'mysite.settings.base'

    os.environ.setdefault("DJANGO_SETTINGS_MODULE", settings_module)

    from django.core.management import execute_from_command_line

    execute_from_command_line(sys.argv)
