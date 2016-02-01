from __future__ import print_function, unicode_literals

from django.core.management.base import BaseCommand

from candidates.models import OrganizationExtra


class Command(BaseCommand):

    def handle(self, *args, **options):

        for party_extra in OrganizationExtra.objects \
                .filter(base__classification='Party') \
                .select_related('base') \
                .prefetch_related('images'):
            images = list(party_extra.images.all())
            if len(images) < 2:
                continue
            print("=====================================================")
            party = party_extra.base
            print(len(images), party_extra.slug, party.name.encode('utf-8'))
            for image in images:
                print('  --')
                print('   ' + image.source.encode('utf-8'))
                print('   ' + image.image.url)
