from collections import defaultdict
from optparse import make_option
from os import chmod, rename
from os.path import dirname
import sys
from tempfile import NamedTemporaryFile

from django.core.management.base import BaseCommand, CommandError

from candidates.csv_helpers import list_to_csv
from candidates.models import PopItPerson
from candidates.popit import PopItApiMixin, popit_unwrap_pagination


class Command(PopItApiMixin, BaseCommand):

    help = "Output CSV files for all elections"
    args = "<BASE-OUTPUT-FILENAME>"

    option_list = BaseCommand.option_list + (
        make_option('-o', '--output',
                    dest='output_filename',
                    help='The filename to write CSV to'),
        make_option('-e', '--election',
                    dest='election',
                    help='The election identifier',
                    default='2015'),
    )

    def handle(self, *args, **options):
        if len(args) != 1:
            msg = "You must supply the prefix for output filenames"
            raise CommandError(msg)
        output_prefix = args[0]
        all_people = []
        election_to_people = defaultdict(list)
        for person_dict in popit_unwrap_pagination(
                self.api.persons,
                embed="membership.organization",
                per_page=100,
        ):
            standing_in = person_dict.get('standing_in')
            if not standing_in:
                continue
            for election in standing_in.keys():
                if not standing_in[election]:
                    continue
                person = PopItPerson.create_from_dict(person_dict)
                person_as_csv_dict = person.as_dict(election=election)
                all_people.append(person_as_csv_dict)
                election_to_people[election].append(person_as_csv_dict)
        elections = election_to_people.keys() + [None]
        for election in elections:
            if election is None:
                output_filename = output_prefix + '-all.csv'
                people_data = all_people
            else:
                output_filename = output_prefix + '-' + election + '.csv'
                people_data = election_to_people[election]
            csv = list_to_csv(people_data)
            # Otherwise write to a temporary file and atomically
            # rename into place:
            ntf = NamedTemporaryFile(
                delete=False,
                dir=dirname(output_filename)
            )
            ntf.write(csv)
            chmod(ntf.name, 0o644)
            rename(ntf.name, output_filename)
