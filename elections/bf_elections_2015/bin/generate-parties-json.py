#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import unicode_literals

import csv
import json
import os
from os.path import dirname, join

data_directory = join(dirname(__file__), '..', 'data')

def get_id(row):
    prefix = {
        'PARTI POLITIQUE': 'pp:',
        'FORMATION POLITIQUE': 'fp:',
        'REGROUPEMENT INDEPENDANT': 'ri:',
    }[row['TYPE']]
    return prefix + row['N°']

parties = []

with open(join(data_directory, 'parties.csv')) as f:
    reader = csv.DictReader(f)
    for row in reader:
        if row['TYPE'] not in ('PARTI POLITIQUE','REGROUPEMENT INDEPENDANT'):
            continue
        party_id = get_id(row)
        parties.append({
            'name': row['DESIGNATION'],
            'classification': 'Party',
            'id': get_id(row),
            'other_names': [
                {
                    'name': row['SIGLE'],
                    'note': 'sigle'
                }
            ],
            'type': row['TYPE'],
        })

with open(join(data_directory, 'all-parties-from-popit.json'), 'w') as fw:
    json.dump(parties, fw, indent=4, sort_keys=True)
