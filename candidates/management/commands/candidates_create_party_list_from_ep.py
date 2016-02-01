from __future__ import unicode_literals

from django.core.management.base import BaseCommand, CommandError
from django.contrib.contenttypes.models import ContentType

import requests
from slugify import slugify

from popolo.models import Organization, Identifier, Source, Link
from candidates.models import OrganizationExtra


class Command(BaseCommand):
    args = "<EP-URL>"
    help = """Create parties from EveryPolitician JSON data

EP-URL should be the URL for the EveryPolitician JSON data for a country.

You can find a link for this on the main country page.
    """

    def handle(self, *args, **options):
        if len(args) != 1:
            raise CommandError("You must provide a URL")

        ep_url, = args

        ep_result = requests.get(ep_url)
        ep_json = ep_result.json()

        orgs = ep_json['organizations']

        for json_org in orgs:
            if json_org['classification'] != 'Party':
                continue

            name = json_org['name']
            slug = slugify(name)
            ep_id = json_org['id']

            org, created = Organization.objects.get_or_create(
                name=name,
                classification='Party'
            )

            content_type = ContentType.objects.get_for_model(org)

            if created:
                Identifier.objects.get_or_create(
                    object_id=org.id,
                    content_type_id=content_type.id,
                    scheme='everypolitician',
                    identifier=ep_id,
                )

                Source.objects.get_or_create(
                    object_id=org.id,
                    content_type_id=content_type.id,
                    url=ep_url,
                    note='Import from EveryPolitician'
                )

            other_ids = json_org.get('identifiers', [])
            for other_id in other_ids:
                Identifier.objects.get_or_create(
                    object_id=org.id,
                    content_type_id=content_type.id,
                    scheme=other_id['scheme'],
                    identifier=other_id['identifier'],
                )

            links = json_org.get('links', [])
            for link in links:
                Link.objects.get_or_create(
                    object_id=org.id,
                    content_type_id=content_type.id,
                    url=link['url'],
                    note=link['note'],
                )

            if created:
                org_extra, _ = OrganizationExtra.objects.get_or_create(
                    base=org
                )

                org_extra.slug = slug
                org_extra.save()
