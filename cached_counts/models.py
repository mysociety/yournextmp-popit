# There a no models needed by this application any more.

from __future__ import unicode_literals

from django.db import connection


def get_attention_needed_posts(max_results=None, random=False):
    from candidates.election_specific import shorten_post_label
    cursor = connection.cursor()
    # This is similar to the query in ConstituencyCountsView,
    # except it's not specific to a particular election and the
    # results are ordered with fewest candidates first:
    query = '''
SELECT pe.slug, p.label, ee.name, ee.slug, count(m.id) as count
  FROM popolo_post p
    INNER JOIN candidates_postextra pe ON pe.base_id = p.id
    INNER JOIN candidates_postextra_elections cppee ON cppee.postextra_id = pe.id
    INNER JOIN elections_election ee ON cppee.election_id = ee.id
    LEFT OUTER JOIN
      (popolo_membership m
        INNER JOIN candidates_membershipextra me
        ON me.base_id = m.id)
      ON m.role = ee.candidate_membership_role AND m.post_id = p.id AND
         me.election_id = ee.id
  GROUP BY pe.slug, p.label, ee.slug, ee.name
  ORDER BY'''
    if random:
        query += ' count, random()'
    else:
        query += ' count, ee.name, p.label'
    if max_results is not None:
        query += ' LIMIT {limit}'.format(limit=max_results)
    cursor.execute(query)
    return [
        {
            'post_slug': row[0],
            'post_label': row[1],
            'election_name': row[2],
            'election_slug': row[3],
            'count': row[4],
            'post_short_label': shorten_post_label(row[1]),
        }
        for row in cursor.fetchall()
    ]
