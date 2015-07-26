import csv
import StringIO

from .models import CSV_ROW_FIELDS

def encode_row_values(d):
    return {
        k: unicode('' if v is None else v).encode('utf-8')
        for k, v in d.items()
    }

def candidate_sort_key(row):
    return (row['election'], row['post_label'], row['name'].split()[-1])

def list_to_csv(candidates_list):
    output = StringIO.StringIO()
    writer = csv.DictWriter(
        output,
        fieldnames=CSV_ROW_FIELDS,
        dialect=csv.excel)
    writer.writeheader()
    for row in sorted(candidates_list, key=candidate_sort_key):
        writer.writerow(encode_row_values(row))
    return output.getvalue()
