#!/usr/bin/env python

from __future__ import unicode_literals

import json
import os
import re
from os.path import dirname, join
from tempfile import NamedTemporaryFile

# We're switching to storing an 'election' attribute on each candidate
# membership that would be associated with a 'standing_in' value, but
# the old test data doesn't have such attributes. This script will
# rewrite all the test data to include these values.

# The test data is all for the 2015 UK general election at the time of
# writing, so this just hardcodes the conditions for the '2010' and
# '2015' elections.

# The original data wasn't necessarily indented consistently or had
# dictionary entries sorted by key, so this also fixes that in the
# test data.

test_data_dir = join(dirname(__file__), '..', 'candidates', 'example-popit-data')

def find_memberships_lists(data):
    membership_lists = []
    if isinstance(data, list):
        for item in data:
            membership_lists += find_memberships_lists(item)
    elif isinstance(data, dict):
        if 'memberships' in data:
            membership_lists.append(data['memberships'])
        for item in data.values():
            membership_lists += find_memberships_lists(item)
    return membership_lists

def update_memberships_list(memberships):
    for m in memberships:
        if m.get('role', '') == 'Candidate':
            start_date = m['start_date']
            end_date = m['end_date']
            if start_date == '2005-05-06' and end_date == '2010-05-06':
                m['election'] = '2010'
            elif start_date == '2010-05-07' and end_date == '9999-12-31':
                m['election'] = '2015'
            else:
                message = "Error: Couldn't find election for {0}"
                raise Exception(message.format(
                    json.dumps(m, indent=4, sort_keys=True)
                ))

def rewrite_json_file(json_filename):
    with open(json_filename) as f:
        data = json.load(f)
        for membership_list in find_memberships_lists(data):
            update_memberships_list(membership_list)
    data_str = json.dumps(data, indent=2, sort_keys=True)
    # The json library outputs with trailing whitespace in some versions
    # strip that before writing out the file again:
    data_str = re.sub(r'(?ms)\s+$', '', data_str)
    with NamedTemporaryFile('w', dir=test_data_dir, delete=False) as ntf:
        ntf.write(data_str)
    os.rename(ntf.name, json_filename)

for leafname in os.listdir(test_data_dir):
    if not leafname.endswith('.json'):
        continue
    rewrite_json_file(join(test_data_dir, leafname))
