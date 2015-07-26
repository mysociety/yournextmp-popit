#!/usr/bin/env python
# coding=UTF-8

import os
from os.path import dirname, join, normpath, realpath, isdir
import sys

script_directory = dirname(realpath(sys.argv[0]))
root_directory = join(script_directory, '..')
root_directory = normpath(root_directory)
elections_directory = join(root_directory, 'elections')

election_options = [
    e for e in os.listdir(elections_directory)
    if isdir(join(elections_directory, e))
]

def usage_and_exit():
    print >> sys.stderr, "Usage: %s <ELECTION>" % (sys.argv[0],)
    print >> sys.stderr, "... where <ELECTION> is one of:"
    for election in election_options:
        print >> sys.stderr, "  ", election
    sys.exit(1)
if len(sys.argv) != 2:
    usage_and_exit()

requested = sys.argv[1]

if requested not in election_options:
    usage_and_exit()

general_yml_symlink = os.path.join(root_directory, 'conf', 'general.yml')
general_yml_target = 'general-' + requested + '.yml'

def switch_link(symlink_filename, target_filename):
    if not os.path.islink(symlink_filename):
        print >> sys.stderr, "%s was not a symlink, and should be" % (symlink_filename,)
        sys.exit(1)
    full_target_filename = os.path.join(os.path.dirname(symlink_filename),
                                        target_filename)
    if not os.path.exists(full_target_filename):
        print >> sys.stderr, "The intended target of the symlink (%s) didn't exist" % (target_filename,)
        sys.exit(1)
    os.unlink(symlink_filename)
    os.symlink(target_filename, symlink_filename)

switch_link(general_yml_symlink, general_yml_target)

# Now touch manage.py to cause a restart if you're running the dev
# server:
os.utime(join(root_directory, 'manage.py'), None)
