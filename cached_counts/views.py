from __future__ import unicode_literals

import json

from django.db import connection
from django.db.models import Count, F
from django.http import HttpResponse

from django.views.generic import TemplateView

from candidates.models import MembershipExtra
from elections.mixins import ElectionMixin
from elections.models import Election
from popolo.models import Membership, Person

from .models import get_attention_needed_posts


def get_prior_election_data(
        total_current, current_election,
        total_prior, prior_election
):
    # Find all those people who are standing in both elections:
    persons_standing_again = list(Person.objects \
        .filter(memberships__extra__election=current_election) \
        .filter(memberships__extra__election=prior_election) \
        .prefetch_related('memberships', 'memberships__extra')
    )
    # Now see how many are standing for the same party in both:
    standing_again = len(persons_standing_again)
    new_candidates = total_current - standing_again
    standing_again_same_party = 0
    for p in persons_standing_again:
        current_party = None
        prior_party = None
        for m in p.memberships.all():
            try:
                extra = m.extra
                if extra.election_id == current_election.id:
                    current_party = m.on_behalf_of_id
                elif extra.election_id == prior_election.id:
                    prior_party = m.on_behalf_of_id
            except MembershipExtra.DoesNotExist:
                # We need this because some memberships may not have
                # an extra.
                pass
        if current_party == prior_party:
            standing_again_same_party += 1
    standing_again_different_party = \
        standing_again - standing_again_same_party
    return {
        'name': prior_election.name,
        'percentage': 100 * float(total_current) / total_prior,
        'new_candidates': new_candidates,
        'standing_again': standing_again,
        'standing_again_different_party': standing_again_different_party,
        'standing_again_same_party': standing_again_same_party,
    }


def get_counts():
    election_id_to_candidates = {
        d['extra__election']: d['count']
        for d in Membership.objects \
            .filter(role=F('extra__election__candidate_membership_role')) \
            .values('extra__election') \
            .annotate(count=Count('extra__election'))
    }
    all_elections_counts = {}
    current_elections = list(Election.objects.current().by_date())
    past_elections = list(Election.objects.current(False).by_date())
    for era, elections in (
            ('current', current_elections),
            ('past', past_elections),
    ):
        all_elections_counts[era] = []
        for e in elections:
            total = election_id_to_candidates.get(e.id, 0)
            election_counts = {
                'id': e.slug,
                'name': e.name,
                'total': total,
            }
            if era == 'current':
                election_counts['prior_elections'] = [
                    get_prior_election_data(
                        total, e,
                        election_id_to_candidates.get(pe.id, 0), pe
                    )
                    for pe in past_elections
                ]
            all_elections_counts[era].append(election_counts)
    return all_elections_counts


class ReportsHomeView(TemplateView):
    template_name = "reports.html"

    def get_context_data(self, **kwargs):
        context = super(ReportsHomeView, self).get_context_data(**kwargs)
        context['all_elections'] = get_counts()
        return context

    def get(self, *args, **kwargs):
        if self.request.GET.get('format') == "json":
            return HttpResponse(
                json.dumps(get_counts()),
                content_type="application/json"
            )
        return super(ReportsHomeView, self).get(*args, **kwargs)


class PartyCountsView(ElectionMixin, TemplateView):
    template_name = "party_counts.html"

    def get_context_data(self, **kwargs):
        context = super(PartyCountsView, self).get_context_data(**kwargs)
        cursor = connection.cursor()
        cursor.execute('''
SELECT oe.slug, o.name, count(m.id) AS count
  FROM popolo_organization o
    INNER JOIN candidates_organizationextra oe ON o.id = oe.base_id
    LEFT OUTER JOIN
      (popolo_membership m
        INNER JOIN candidates_membershipextra me ON me.base_id = m.id
        INNER JOIN elections_election ee ON me.election_id = ee.id AND ee.id = %s)
      ON o.id = m.on_behalf_of_id
  WHERE o.classification = 'Party'
  GROUP BY oe.slug, o.name
  ORDER BY count DESC, o.name;
        ''', [self.election_data.id])
        context['party_counts'] = [
            {
                'party_slug': row[0],
                'party_name': row[1],
                'count': row[2],
            }
            for row in cursor.fetchall()
        ]
        return context


class ConstituencyCountsView(ElectionMixin, TemplateView):
    template_name = "constituency_counts.html"

    def get_context_data(self, **kwargs):
        from candidates.election_specific import shorten_post_label
        context = super(ConstituencyCountsView, self).get_context_data(**kwargs)
        cursor = connection.cursor()
        cursor.execute('''
SELECT pe.slug, p.label, count(m.id) as count
  FROM popolo_post p
    INNER JOIN candidates_postextra pe ON pe.base_id = p.id
    INNER JOIN candidates_postextra_elections cppee ON cppee.postextra_id = pe.id
    INNER JOIN elections_election ee ON cppee.election_id = ee.id AND ee.id = %s
    LEFT OUTER JOIN
      (popolo_membership m
        INNER JOIN candidates_membershipextra me
        ON me.base_id = m.id)
      ON m.role = ee.candidate_membership_role AND m.post_id = p.id AND
         me.election_id = ee.id
  GROUP BY pe.slug, p.label
  ORDER BY count DESC;
        ''', [self.election_data.id])
        context['post_counts'] = [
            {
                'post_slug': row[0],
                'post_label': row[1],
                'count': row[2],
                'post_short_label': shorten_post_label(row[1]),
            }
            for row in cursor.fetchall()
        ]
        return context


class AttentionNeededView(TemplateView):
    template_name = "attention_needed.html"

    def get_context_data(self, **kwargs):
        context = super(AttentionNeededView, self).get_context_data(**kwargs)
        context['post_counts'] = get_attention_needed_posts()
        return context
