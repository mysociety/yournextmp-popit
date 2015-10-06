#!/usr/bin/env python
# -*- coding: utf-8 -*-

import csv
import re
import requests
import time

from bs4 import BeautifulSoup

ynmp_to_bbc_party = {
    'Conservative Party': 'CON',
    'Labour Party': 'LAB',
    'Labour and Co-operative Party': 'LAB',
    'Scottish National Party (SNP)': 'SNP',
    'Liberal Democrats': 'LD',
    'Democratic Unionist Party - D.U.P.': 'DUP',
    'Sinn Féin': 'SF',
    'Plaid Cymru - The Party of Wales': 'PC',
    'SDLP (Social Democratic & Labour Party)': 'SDLP',
    'Ulster Unionist Party': 'UUP',
    'UK Independence Party (UKIP)': 'UKIP',
    'Green Party': 'GRN',
    'Speaker seeking re-election': 'SPE',
    'Independent': 'IND',
}

r = requests.get(
    'https://edit.yournextmp.com/media/candidates.csv',
    stream=True,
    verify=False,
)
reader = csv.DictReader(r.raw)
for row in reader:
    gss_code = row['gss_code']
    cons_name = row['constituency']
    elected = row['elected']
    if elected == '':
        msg = "In {cons_name} {person_name} ({person_id}) had no elected status"
        raise Exception, msg.format(
            cons_name=cons_name,
            person_name=row['name'],
            person_id=row['id'],
        )
    if not elected.lower() == 'true':
        continue
    if cons_name < 'South Thanet':
        continue
    party_from_ynmp = ynmp_to_bbc_party[row['party']]
    print "got:", gss_code, cons_name, party_from_ynmp
    # Now fetch the corresponding page from the BBC:
    bbc_url = 'http://www.bbc.co.uk/news/politics/constituencies/' + gss_code
    bbc_r = requests.get(bbc_url)
    # time.sleep(2)
    soup = BeautifulSoup(bbc_r.content)
    party_names_short = soup.find_all('div', {'class': 'party__name--short'})
    bracketed_party_abbr = party_names_short[0].text
    m = re.search(r'^\s*\(\s*(\w+)\s*\)\s*$', bracketed_party_abbr)
    if not m:
        print "Couldn't find party abbreviation:", m.group(1)
    bbc_winner_party_name = m.group(1)
    if bbc_winner_party_name != party_from_ynmp:
        msg = "In {cons_name} YNMP had {ynmp}, the BBC had {bbc}"
        raise Exception, msg.format(
            cons_name=cons_name,
            ynmp=party_from_ynmp,
            bbc=bbc_winner_party_name,
        )
