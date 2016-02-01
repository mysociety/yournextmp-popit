from __future__ import print_function, unicode_literals

from collections import defaultdict
from datetime import date
import re

from django.core.management.base import BaseCommand
from django.db import transaction

from popolo.models import Organization

from candidates.models import OrganizationExtra

def fix_joint_party_name(joint_party_name):
    return {
        'The Christian Party Christian Peoples Alliance':
        'Christian Party Christian Peoples Alliance'
    }.get(joint_party_name, joint_party_name)

def extract_number_from_id(party_id):
    m = re.search('\d+', party_id)
    if m:
        return int(m.group(0), 10)
    return -1

def create_or_update_party(joint_party_name, sub_parties):
    party_ids = sorted(
        extract_number_from_id(p.extra.slug)
        for p in sub_parties
    )
    registers = set(p.extra.register for p in sub_parties)
    if len(registers) > 1:
        raise Exception("Multiple registers found " + repr(registers))
    joint_party_id = 'joint-party:' + '-'.join(str(i) for i in party_ids)
    if not OrganizationExtra.objects.filter(slug=joint_party_id).exists():
        joint_party = Organization.objects.create(
            name=joint_party_name,
            classification='Party',
            dissolution_date='9999-12-31',
        )
        OrganizationExtra.objects.create(
            base=joint_party,
            slug=joint_party_id,
            register=next(iter(registers)),
        )


joint_description_re = re.compile(
    r'^(?P<joint_name>.*?) \([jJ]oint [dD]escriptions? with (?P<sub_party>.*)\)'
)


class Command(BaseCommand):
    help = "Create joint pseudo-parties based on parties with joint descriptions"

    def handle(self, **options):
        joint_party_to_sub_parties = defaultdict(list)
        for party_extra in OrganizationExtra.objects.filter(
                base__classification='Party'
        ).select_related('base'):
            party = party_extra.base
            today_str = str(date.today())
            if party.dissolution_date and (party.dissolution_date < today_str):
                continue
            descriptions = party.other_names.filter(
                note='registered-description'
            )
            for description_with_translation in descriptions:
                d = re.split(r'\s*\|\s*', description_with_translation.name)[0]
                m = joint_description_re.search(d)
                if not m:
                    continue
                joint_name = fix_joint_party_name(m.group('joint_name'))
                joint_party_to_sub_parties[joint_name].append(party)
        with transaction.atomic():
            for joint_name, sub_parties in joint_party_to_sub_parties.items():
                if len(sub_parties) < 2:
                    message = 'Ignoring "{joint_name}"' \
                        ' (only made up of one party: "{sub_party}")'
                    print(message.format(
                        joint_name=joint_name,
                        sub_party=sub_parties[0].name
                    ))
                    continue
                message = 'Creating "{joint_name}", made up of: {sub_parties}'
                print(message.format(
                    joint_name=joint_name,
                    sub_parties=sub_parties,
                ))

                create_or_update_party(joint_name, sub_parties)
