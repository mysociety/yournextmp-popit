from __future__ import unicode_literals

import json
from os.path import dirname
import subprocess
import sys
from datetime import date

import django
from django.contrib.auth.models import User
from django.db.models import Count, Prefetch
from django.http import HttpResponse
from django.views.generic import View

from images.models import Image
from candidates import serializers
from candidates import models as extra_models
from elections.models import AreaType, Election
from popolo.models import Area, Membership, Person, Post
from rest_framework import viewsets

from compat import text_type

from ..election_specific import fetch_area_ids


class UpcomingElectionsView(View):

    http_method_names = ['get']

    def get(self, request, *args, **kwargs):
        postcode = request.GET.get('postcode', None)
        coords = request.GET.get('coords', None)

        # TODO: postcode may not make sense everywhere
        errors = None
        if not postcode and not coords:
            errors = {
                'error': 'Postcode or Co-ordinates required'
            }

        try:
            areas = fetch_area_ids(postcode=postcode, coords=coords)
        except Exception as e:
            errors = {
                'error': e.message
            }

        if errors:
            return HttpResponse(
                json.dumps(errors), status=400, content_type='application/json'
            )

        area_ids = [area[1] for area in areas]

        posts = Post.objects.filter(
            area__identifier__in=area_ids,
        ).select_related(
            'area', 'area__extra__type', 'organization'
        ).prefetch_related(
            'extra__elections'
        )

        results = []
        for post in posts.all():
            election = post.extra.elections.get(
                current=True,
                election_date__gte=date.today()
            )
            if election:
                results.append({
                    'post_name': post.label,
                    'organization': post.organization.name,
                    'area': {
                        'type': post.area.extra.type.name,
                        'name': post.area.name,
                        'identifier': post.area.identifier,
                    },
                    'election_date': text_type(election.election_date),
                    'election_name': election.name
                })

        return HttpResponse(
            json.dumps(results), content_type='application/json'
        )


class VersionView(View):

    http_method_names = ['get']

    def get(self, request, *args, **kwargs):
        result = {
            'python_version': sys.version,
            'django_version': django.get_version(),
            'interesting_user_actions': extra_models.LoggedAction.objects \
                .exclude(action_type='set-candidate-not-elected') \
                .count(),
            'users_who_have_edited': User.objects \
                .annotate(edit_count=Count('loggedaction')) \
                .filter(edit_count__gt=0).count()
        }
        # Try to get the object name of HEAD from git:
        try:
            git_version = subprocess.check_output(
                ['git', 'rev-parse', '--verify', 'HEAD'],
                cwd=dirname(__file__),
                universal_newlines=True
            ).strip()
            result['git_version'] = git_version
        except (OSError, subprocess.CalledProcessError):
            pass
        return HttpResponse(
            json.dumps(result), content_type='application/json'
        )


class PostIDToPartySetView(View):

    http_method_names = ['get']

    def get(self, request, *args, **kwargs):
        result = dict(
            extra_models.PostExtra.objects.filter(elections__current=True) \
               .values_list('slug', 'party_set__slug')
        )
        return HttpResponse(
            json.dumps(result), content_type='application/json'
        )


# Now the django-rest-framework based API views:

class PersonViewSet(viewsets.ModelViewSet):
    queryset = Person.objects \
        .select_related('extra') \
        .prefetch_related(
            Prefetch(
                'memberships',
                Membership.objects.select_related(
                    'on_behalf_of__extra',
                    'organization__extra',
                    'post__extra',
                    'extra',
                )
            ),
            'memberships__extra__election',
            'memberships__organization__extra',
            'extra__images',
            'other_names',
            'contact_details',
            'links',
            'identifiers',
        ) \
        .order_by('id')
    serializer_class = serializers.PersonSerializer


class OrganizationViewSet(viewsets.ModelViewSet):
    queryset = extra_models.OrganizationExtra.objects \
        .select_related('base') \
        .prefetch_related(
            'images',
            'images__extra',
            'base__contact_details',
            'base__other_names',
            'base__sources',
            'base__links',
            'base__identifiers',
            'base__parent',
            'base__parent__extra',
        ) \
        .order_by('base__id')
    lookup_field = 'slug'
    serializer_class = serializers.OrganizationExtraSerializer


class PostViewSet(viewsets.ModelViewSet):
    queryset = extra_models.PostExtra.objects \
        .select_related(
            'base__organization__extra',
            'base__area__extra',
        ) \
        .prefetch_related(
            'elections',
            'elections__area_types',
            'base__area__other_identifiers',
            'base__memberships',
        ) \
        .order_by('base__id')
    lookup_field = 'slug'
    serializer_class = serializers.PostExtraSerializer


class AreaViewSet(viewsets.ModelViewSet):
    queryset = Area.objects \
        .prefetch_related('extra') \
        .order_by('id')
    serializer_class = serializers.AreaSerializer


class AreaTypeViewSet(viewsets.ModelViewSet):
    queryset = AreaType.objects.order_by('id')
    serializer_class = serializers.AreaTypeSerializer


class ElectionViewSet(viewsets.ModelViewSet):
    queryset = Election.objects.order_by('id')
    lookup_field = 'slug'
    serializer_class = serializers.ElectionSerializer


class PartySetViewSet(viewsets.ModelViewSet):
    queryset = extra_models.PartySet.objects.order_by('id')
    serializer_class = serializers.PartySetSerializer


class ImageViewSet(viewsets.ModelViewSet):
    queryset = Image.objects.order_by('id')
    serializer_class = serializers.ImageSerializer


class MembershipViewSet(viewsets.ModelViewSet):
    queryset = Membership.objects.order_by('id')
    serializer_class = serializers.MembershipSerializer


class LoggedActionViewSet(viewsets.ModelViewSet):
    queryset = extra_models.LoggedAction.objects.order_by('id')
    serializer_class = serializers.LoggedActionSerializer


class ExtraFieldViewSet(viewsets.ModelViewSet):
    queryset = extra_models.ExtraField.objects.order_by('id')
    serializer_class = serializers.ExtraFieldSerializer
