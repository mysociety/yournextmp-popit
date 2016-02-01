from __future__ import unicode_literals

from compat import StreamDictWriter
from .models import CSV_ROW_FIELDS


def _candidate_sort_key(row):
    return (row['election'], row['post_label'], row['name'].split()[-1])


def list_to_csv(candidates_list):
    from .election_specific import EXTRA_CSV_ROW_FIELDS
    csv_fields = CSV_ROW_FIELDS + EXTRA_CSV_ROW_FIELDS
    writer = StreamDictWriter(fieldnames=csv_fields)
    writer.writeheader()
    for row in sorted(candidates_list, key=_candidate_sort_key):
        writer.writerow(row)
    return writer.output
