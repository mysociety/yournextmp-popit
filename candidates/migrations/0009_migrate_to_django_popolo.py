# -*- coding: utf-8 -*-
from __future__ import print_function, unicode_literals

import errno
import hashlib
import json
import os
from os.path import join, exists, dirname
import re
import requests
import shutil

from PIL import Image as PillowImage

from django.conf import settings
from django.core.files.storage import FileSystemStorage
from django.core.management.color import no_style
from django.db import connection, migrations
from django.db.models import Count
from django.utils.six.moves.urllib_parse import urlsplit

from popolo.importers.popit import PopItImporter, show_data_on_error

PILLOW_FORMAT_EXTENSIONS = {
    'JPEG': 'jpg',
    'PNG': 'png',
    'GIF': 'gif',
    'BMP': 'bmp',
}

CACHE_DIRECTORY = join(dirname(__file__), '.download-cache')

def get_url_cached(url):
    try:
        os.makedirs(CACHE_DIRECTORY)
    except OSError as e:
        if e.errno != errno.EEXIST:
            raise
    filename = join(CACHE_DIRECTORY, hashlib.md5(url).hexdigest())
    if exists(filename):
        return filename
    else:
        print("\nDownloading {0} ...".format(url))
        with open(filename, 'wb') as f:
            r = requests.get(url, stream=True)
            r.raise_for_status()
            r.raw.decode_content = True
            shutil.copyfileobj(r.raw, f)
        print("done")
    return filename

class YNRPopItImporter(PopItImporter):

    person_id_to_json_data = {}

    def __init__(self, apps, schema_editor):
        self.apps = apps
        self.schema_editor = schema_editor
        self.image_storage = FileSystemStorage()
        Election = self.get_model_class('elections', 'Election')
        self.election_cache = {
            e.slug: e for e in Election.objects.all()
        }
        self.uk_mapit_data = {}

    def get_model_class(self, app_label, model_name):
        return self.apps.get_model(app_label, model_name)

    def get_images_for_object(self, images_data, django_extra_object):
        User = self.get_model_class('auth', 'User')
        ContentType = self.get_model_class('contenttypes', 'ContentType')
        person_extra_content_type = ContentType.objects.get_for_model(django_extra_object)

        # Now download and import all the images:
        Image = self.get_model_class('images', 'Image')
        ImageExtra = self.get_model_class('candidates', 'ImageExtra')
        first_image = True
        for image_data in images_data:
            with show_data_on_error('image_data', image_data):
                url = image_data['url']
                try:
                    image_filename = get_url_cached(url)
                except requests.exceptions.HTTPError as e:
                    msg = "Ignoring image URL {url}, with status code {status}"
                    print(msg.format(
                        url=url,
                        status=e.response.status_code
                    ))
                    continue
                with open(image_filename, 'rb') as f:
                    md5sum = hashlib.md5(f.read()).hexdigest()
                with open(image_filename, 'rb') as f:
                    try:
                        pillow_image = PillowImage.open(f)
                    except IOError as e:
                        if 'cannot identify image file' in e.args[0]:
                            print("Ignoring a non-image file {0}".format(
                                image_filename
                            ))
                            continue
                        raise
                    extension = PILLOW_FORMAT_EXTENSIONS[pillow_image.format]
                suggested_filename = join(
                    'images', image_data['id'] + '.' + extension
                )
                with open(image_filename, 'rb') as f:
                    storage_filename = self.image_storage.save(
                        suggested_filename, f
                    )
                image_uploaded_by = image_data.get('uploaded_by_user', '')
                try:
                    uploading_user = User.objects.get(username=image_uploaded_by)
                except User.DoesNotExist:
                    uploading_user = None
                image_copyright = image_data.get('moderator_why_allowed', '')
                image_user_copyright = image_data.get('user_why_allowed', '')
                image_justification = image_data.get('user_justification_for_use', '')
                image_notes = image_data.get('notes', '')
                image_source = image_data.get('source', '')
                image = Image.objects.create(
                    image=storage_filename,
                    source=image_source,
                    is_primary=first_image,
                    object_id=django_extra_object.id,
                    content_type_id=person_extra_content_type.id
                )


                ImageExtra.objects.create(
                    base=image,
                    copyright=image_copyright,
                    uploading_user=uploading_user,
                    user_notes=image_justification,
                    md5sum=md5sum,
                    user_copyright=image_user_copyright,
                    notes=image_notes,
                )

            if first_image:
                first_image = False

    def update_person(self, person_data):
        new_person_data = person_data.copy()
        # There are quite a lot of summary fields in PopIt that are
        # way longer than 1024 characters.
        new_person_data['summary'] = (person_data.get('summary') or '')[:1024]
        # Surprisingly, quite a lot of PopIt email addresses have
        # extraneous whitespace in them, so strip any out to avoid
        # the 'Enter a valid email address' ValidationError on saving:
        email = person_data.get('email') or None
        if email:
            email = re.sub(r'\s*', '', email)
        new_person_data['email'] = email
        # We would like people to have the same ID as they did in
        # PopIt (where the person IDs were just stringified
        # integers). So create a minimal person with the right ID and
        # an identifier to that the method we're overriding will
        # notice that it exists.  n.b. this means we have to reset the
        # person id sequence at the end of import_from_popit
        Person = self.get_popolo_model_class('Person')
        minimal_person = Person.objects.create(
            id=int(person_data['id']),
            name=person_data['name'],
        )
        self.create_identifier('person', person_data['id'], minimal_person)
        # Now the superclass method should find and update that person.
        person_id, person = super(YNRPopItImporter, self).update_person(
            new_person_data
        )

        self.person_id_to_json_data[person_data['id']] = new_person_data

        # Create the extra person object:
        PersonExtra = self.get_model_class('candidates', 'PersonExtra')
        extra = PersonExtra.objects.create(
            base=person,
            versions=json.dumps(new_person_data['versions'])
        )

        # Record the elections that the person definitely isn't
        # standing in:
        standing_in = new_person_data.get('standing_in') or {}
        for election_slug, standing_in_election in standing_in.items():
            if standing_in_election is None:
                extra.not_standing.add(self.election_cache[election_slug])

        self.get_images_for_object(person_data['images'], extra)

        return person_id, person

    def update_organization(self, org_data, area):
        org_id, org = super(YNRPopItImporter, self).update_organization(
            org_data, area
        )

        # Create the extra organization object:
        OrganizationExtra = self.get_model_class('candidates', 'OrganizationExtra')
        register = org_data.get('register') or ''
        extra = OrganizationExtra.objects.create(
            base=org,
            slug=org_data['id'],
            register=register,
        )

        self.get_images_for_object(org_data['images'], extra)

        return org_id, org

    def update_area(self, area_data):
        new_area_data = area_data.copy()
        if settings.ELECTION_APP == 'uk_general_election_2015' or \
           settings.ELECTION_APP == 'ar_elections_2015' or \
           settings.ELECTION_APP == 'bf_elections_2015':
            identifier = new_area_data['identifier']
            split_url = urlsplit(identifier)
            if not (split_url.netloc.endswith('mapit.mysociety.org') or
                    split_url.netloc.endswith('mapit.staging.mysociety.org')):
                raise Exception("Area identifers are expected to be MapIt area URLs")
            mapit_area_url = identifier
            m = re.search(r'^/area/(\d+)$', split_url.path)
            if not m:
                message = "The format of the MapIt URL was unexpected: {0}"
                raise Exception(message.format(mapit_area_url))
            mapit_area_id = m.group(1)
            # Make the Area.identifier for UK areas just the integer
            # MapIt Area ID to make it easy to keep area URLs the same:
            new_area_data['identifier'] = mapit_area_id
        elif settings.ELECTION_APP == 'st_paul_municipal_2015':
            old_identifier = new_area_data['identifier']
            if old_identifier == '/area/0':
                new_area_data['identifier'] = 'ocd-division/country:us/state:mn/place:st_paul'
            else:
                m = re.search(r'^/area/([1-7])', old_identifier)
                if m:
                    new_area_data['identifier'] = \
                        'ocd-division/country:us/state:mn/place:st_paul/ward:' + m.group(1)
                else:
                    message = "The format of the St Paul area ID was unexpected: {0}"
                    raise Exception(message.format(old_identifier))

        area_id, area = super(YNRPopItImporter, self).update_area(new_area_data)

        if settings.ELECTION_APP == 'uk_general_election_2015':
            ContentType = self.get_model_class('contenttypes', 'ContentType')
            area_content_type = ContentType.objects.get_for_model(area)
            Identifier = self.get_model_class('popolo', 'Identifier')
            # For the UK, we need to add the GSS code for each area:
            mapit_filename = get_url_cached(mapit_area_url)
            with open(mapit_filename) as f:
                mapit_area_data = json.load(f)
            self.uk_mapit_data[str(mapit_area_data['id'])] = mapit_area_data
            gss_code = mapit_area_data.get('codes', {}).get('gss')
            if gss_code:
                Identifier.objects.create(
                    scheme='gss',
                    identifier=gss_code,
                    object_id=area.id,
                    content_type_id=area_content_type.id,
                )
            # Also preserve the complete MapIt URL:
            Identifier.objects.create(
                scheme='mapit-area-url',
                identifier=mapit_area_url,
                object_id=area.id,
                content_type_id=area_content_type.id
            )
        # Create the extra area object:
        AreaExtra = self.get_model_class('candidates', 'AreaExtra')
        AreaExtra.objects.get_or_create(base=area)

        return area_id, area

    def update_post(self, post_data, area, org_id_to_django_object):
        post_id, post = super(YNRPopItImporter, self).update_post(post_data, area, org_id_to_django_object)

        PostExtra = self.get_model_class('candidates', 'PostExtra')
        post_extra, created = PostExtra.objects.get_or_create(base=post, slug=post_data['id'])
        post_extra.candidates_locked = post_data.get('candidates_locked', False)
        post_extra.save()

        area_types = set()
        for election_slug in post_data['elections']:
            election = self.election_cache[election_slug]
            post_extra.elections.add(election)
            for area_type in election.area_types.all():
                area_types.add(area_type)

        if len(area_types) > 1:
            message = "Only one area type is allowed per election in this " \
                "migration, but for post ({post_id}) found {area_types}".format(
                    post_id=post_data['id'], area_types=area_types
            )
            raise Exception(message)

        only_area_type = next(iter(area_types))
        area.extra.type = only_area_type
        area.extra.save()

        PartySet = self.get_model_class('candidates', 'partyset')
        # Set the post group (which is only actually needed for the
        # UK) and party set for each post.
        if settings.ELECTION_APP == 'uk_general_election_2015':
            mapit_area_data = self.uk_mapit_data[area.identifier]
            country_name = mapit_area_data['country_name']
            post_extra.group = country_name
            if country_name == 'Northern Ireland':
                post_extra.party_set = PartySet.objects.get(slug='ni')
            elif country_name in ('England', 'Scotland', 'Wales'):
                post_extra.party_set = PartySet.objects.get(slug='gb')
        elif settings.ELECTION_APP == 'bf_elections_2015':
            post_extra.party_set = PartySet.objects.get(slug='national')
        elif settings.ELECTION_APP == 'st_paul_municipal_2015':
            post_extra.party_set = PartySet.objects.get(slug='st-paul')
        elif settings.ELECTION_APP == 'ar_elections_2015':
            party_set_name = AR_AREA_NAME_TO_PARTY_SET_NAME.get(area.name)
            if party_set_name:
                post_extra.party_set = PartySet.objects.get(name=party_set_name)
            else:
                print("Couldn't find party set from name {0}".format(area.name))
                post_extra.party_set = PartySet.objects.get(slug='nacional')
        post_extra.save()

        return post_id, post

    def update_membership(
        self,
        membership_data,
        area,
        org_id_to_django_object,
        post_id_to_django_object,
        person_id_to_django_object,
    ):
        new_membership_data = membership_data.copy()
        if settings.ELECTION_APP == 'st_paul_municipal_2015':
            # For some reason some posts in the St Paul PopIt have an
            # organization_id of 'commons' although that organization
            # doesn't exist. (sigh that PopIt allowed that...)
            if new_membership_data.get('organization_id') == 'commons':
                new_membership_data['organization_id'] = 'saint-paul-city-council'

        membership_id, membership = super(YNRPopItImporter, self).update_membership(
            new_membership_data,
            area,
            org_id_to_django_object,
            post_id_to_django_object,
            person_id_to_django_object,
        )
        Election = self.get_model_class('elections', 'Election')

        election_slug = new_membership_data.get('election', None)
        # This is an unfortunate fixup to have to do. It seems that
        # the scripts that we used to make sure that all memberships
        # representing candidacies had an 'election' property didn't
        # work consistently; lots of candidacies are missing it.  So,
        # if it looks as if the membership is a candidacy and it's
        # missing its election property, set it. This inference
        # wouldn't work in general but should work for all the data in
        # the known YNR instances based on PopIt:
        candidacy = membership.role.lower() not in (None, '', 'member')
        if (not election_slug) and candidacy and membership.post:
            matching_elections = list(Election.objects.filter(
                for_post_role=membership.post.role,
                candidate_membership_role=membership.role,
                election_date__gte=membership.start_date,
                election_date__lte=membership.end_date,
                organization_name=membership.post.organization.name,
            ))
            # If there's exactly one matching election, that's ideal:
            if len(matching_elections) == 1:
                election_slug = matching_elections[0].slug
            # If we hit the ambiguity between the two types of
            # Parlamentario Mercosur, there's a special case for that:
            elif len(matching_elections) == 2 and \
                    (membership.post.role == 'Parlamentario Mercosur'):
                if membership.post.slug == 'pmeu':
                    election_slug = 'parlamentarios-mercosur-unico-paso-2015'
                else:
                    election_slug = 'parlamentarios-mercosur-regional-paso-2015'
            else:
                raise Exception("Election missing on membership, and no unique matching election found")
        if election_slug is not None:
            election = Election.objects.get(slug=election_slug)

            if membership.role == election.candidate_membership_role:
                MembershipExtra = self.get_model_class('candidates', 'MembershipExtra')
                me, created = MembershipExtra.objects.get_or_create(
                    base=membership,
                    election=election
                )

                person_data = self.person_id_to_json_data[new_membership_data['person_id']]
                party = person_data['party_memberships'].get(election.slug)
                if party is not None:
                    membership.on_behalf_of = org_id_to_django_object[party['id']]
                    membership.save()

                party_list_position = new_membership_data.get('party_list_position', None)
                if party_list_position is not None:
                    if me:
                        me.party_list_position = party_list_position
                        me.save()

                standing_in = person_data['standing_in'].get(election.slug)
                if standing_in is not None:
                    if me:
                        me.elected = standing_in.get('elected', None)
                        me.save()

        start_date = new_membership_data.get('start_date', None)
        end_date = new_membership_data.get('end_date', None)

        if start_date is not None:
            membership.start_date = start_date
        if end_date is not None:
            membership.end_date = end_date

        membership.save()
        return membership_id, membership

    def make_contact_detail_dict(self, contact_detail_data):
        new_contact_detail_data = contact_detail_data.copy()
        # There are some contact types that are used in PopIt that are
        # longer than 12 characters...
        new_contact_detail_data['type'] = contact_detail_data['type'][:12]
        return super(YNRPopItImporter, self).make_contact_detail_dict(new_contact_detail_data)

    def make_link_dict(self, link_data):
        new_link_data = link_data.copy()
        # There are some really long URLs in PopIt, which exceed the
        # 200 character limit in django-popolo.
        new_link_data['url'] = new_link_data['url'][:200]
        return super(YNRPopItImporter, self).make_link_dict(new_link_data)


PARTY_SETS_BY_ELECTION_APP = {
    'uk_general_election_2015': [
        {'slug': 'gb', 'name': 'Great Britain'},
        {'slug': 'ni', 'name': 'Northern Ireland'},
    ],
    'st_paul_municipal_2015': [
        {'slug': 'st-paul', 'name': 'Saint Paul, Minnesota'},
    ],
    'ar_elections_2015': [
        {'slug': 'jujuy', 'name': 'Jujuy'},
        {'slug': 'la-rioja', 'name': 'La Rioja'},
        {'slug': 'catamarca', 'name': 'Catamarca'},
        {'slug': 'salta', 'name': 'Salta'},
        {'slug': 'nacional', 'name': 'Nacional'},
        {'slug': 'chaco', 'name': 'Chaco'},
        {'slug': 'mendoza', 'name': 'Mendoza'},
        {'slug': 'chubut', 'name': 'Chubut'},
        {'slug': 'capital-federal', 'name': 'Capital Federal'},
        {'slug': 'neuquen', 'name': 'Neuqu\xe9n'},
        {'slug': 'san-juan', 'name': 'San Juan'},
        {'slug': 'corrientes', 'name': 'Corrientes'},
        {'slug': 'la-pampa', 'name': 'La Pampa'},
        {'slug': 'formosa', 'name': 'Formosa'},
        {'slug': 'misiones', 'name': 'Misiones'},
        {'slug': 'cordoba', 'name': 'C\xf3rdoba'},
        {'slug': 'santiago-del-estero', 'name': 'Santiago Del Estero'},
        {'slug': 'san-luis', 'name': 'San Luis'},
        {'slug': 'buenos-aires', 'name': 'Buenos Aires'},
        {'slug': 'santa-cruz', 'name': 'Santa Cruz'},
        {'slug': 'rio-negro', 'name': 'R\xedo Negro'},
        {'slug': 'santa-fe', 'name': 'Santa Fe'},
        {'slug': 'tucuman', 'name': 'Tucum\xe1n'},
        {'slug': 'tierra-del-fuego', 'name': 'Tierra del Fuego'},
        {'slug': 'entre-rios', 'name': 'Entre R\xedos'}
    ],
    'bf_elections_2015': [
        {'slug': 'national', 'name': 'National'},
    ],
}

ELECTION_APPS_WITH_EXISTING_DATA = (
    'ar_elections_2015',
    'bf_elections_2015',
    'st_paul_municipal_2015',
    'uk_general_election_2015',
)

AR_AREA_NAME_TO_PARTY_SET_NAME = {
    "BUENOS AIRES": "Buenos Aires",
    "CIUDAD AUTONOMA DE BUENOS AIRES": "Capital Federal",
    "CATAMARCA": "Catamarca",
    "CHACO": "Chaco",
    "CHUBUT": "Chubut",
    "CORDOBA": "Córdoba",
    "CORRIENTES": "Corrientes",
    "ENTRE RIOS": "Entre Ríos",
    "FORMOSA": "Formosa",
    "JUJUY": "Jujuy",
    "LA PAMPA": "La Pampa",
    "LA RIOJA": "La Rioja",
    "MENDOZA": "Mendoza",
    "MISIONES": "Misiones",
    "Argentina": "Nacional",
    "NEUQUEN": "Neuquén",
    "RIO NEGRO": "Río Negro",
    "SALTA": "Salta",
    "SAN JUAN": "San Juan",
    "SAN LUIS": "San Luis",
    "SANTA CRUZ": "Santa Cruz",
    "SANTA FE": "Santa Fe",
    "SANTIAGO DEL ESTERO": "Santiago Del Estero",
    "TIERRA DEL FUEGO, ANTARTIDA E ISLAS DEL ATLANTICO SUR": "Tierra del Fuego",
    "TUCUMAN": "Tucumán",
}

def import_from_popit(apps, schema_editor):
    if settings.ELECTION_APP not in ELECTION_APPS_WITH_EXISTING_DATA:
        return
    if settings.RUNNING_TESTS:
        return
    # Create the party sets for this country:
    party_set_from_slug = {}
    party_set_from_name = {}
    for party_set_data in PARTY_SETS_BY_ELECTION_APP.get(
            settings.ELECTION_APP, []
    ):
        PartySet = apps.get_model('candidates', 'partyset')
        party_set = PartySet.objects.create(**party_set_data)
        party_set_from_slug[party_set_data['slug']] = party_set
        party_set_from_name[party_set_data['name']] = party_set
    # Now run the standard import:
    importer = YNRPopItImporter(apps, schema_editor)
    host_and_port = {
        'uk_general_election_2015': 'yournextmp.popit.mysociety.org:80',
        'ar_elections_2015': 'ynr-argentina.popit.mysociety.org:80',
        'bf_elections_2015': 'burkina-faso.popit.mysociety.org:80',
        'st_paul_municipal_2015': 'twincities.popit.mysociety.org:80',
    }[settings.ELECTION_APP]
    url = 'http://{host_and_port}/api/v0.1/export.json'.format(
        host_and_port=host_and_port
    )
    export_filename = get_url_cached(url)
    importer.import_from_export_json(export_filename)
    # Now reset the database sequence for popolo_person's id field,
    # since we've specified the id when creating each person.
    Person = apps.get_model('popolo', 'person')
    reset_sql_list = connection.ops.sequence_reset_sql(
        no_style(), [Person]
    )
    if reset_sql_list:
        cursor = connection.cursor()
        for reset_sql in reset_sql_list:
            cursor.execute(reset_sql)
    # For Argentina, we need the original party JSON to decide on the
    # party sets.
    if settings.ELECTION_APP == 'ar_elections_2015':
        ar_party_id_to_party_sets = {}
        ar_filename = join(
            dirname(__file__), '..', '..', 'elections', 'ar_elections_2015',
            'data', 'all-parties-from-popit.json'
        )
        with open(ar_filename) as f:
            ar_all_party_data = json.load(f)
            for party_data in ar_all_party_data:
                territory = party_data.get('territory')
                if territory:
                    party_set = party_set_from_name[territory]
                    ar_party_id_to_party_sets[party_data['id']] = \
                        [party_set]
                else:
                    ar_party_id_to_party_sets[party_data['id']] = \
                        party_set_from_name.values()

    # And add each party to a party set:
    Organization = apps.get_model('popolo', 'organization')
    for party in Organization.objects.filter(
            classification='Party',
    ).prefetch_related('extra'):
        if settings.ELECTION_APP == 'bf_elections_2015':
            party.party_sets.add(party_set_from_slug['national'])
        elif settings.ELECTION_APP == 'st_paul_municipal_2015':
            party.party_sets.add(party_set_from_slug['st-paul'])
        elif settings.ELECTION_APP == 'uk_general_election_2015':
            register = party.extra.register
            if register == 'Great Britain':
                party.party_sets.add(party_set_from_slug['gb'])
            elif register == 'Northern Ireland':
                party.party_sets.add(party_set_from_slug['ni'])
            else:
                party.party_sets.add(*PartySet.objects.all())
        elif settings.ELECTION_APP == 'ar_elections_2015':
            party_sets = ar_party_id_to_party_sets[party.extra.slug]
            party.party_sets.add(*party_sets)
    # It turns out that there were quite a lot of duplicate
    # memberships in the old YNR PopIt instances, so try to remove any
    # duplicates:
    Membership = apps.get_model('popolo', 'membership')
    for duplicate in Membership.objects.values(
            'label',
            'role',
            'person_id',
            'organization_id',
            'on_behalf_of',
            'post_id',
            'start_date',
            'end_date',
            'role',
            'extra__election__slug') \
        .annotate(Count('id')).filter(id__count__gt=1):
        del duplicate['id__count']
        for membership in Membership.objects.filter(**duplicate)[1:]:
            membership.delete()

    # Also remove any old-style party memberships - these are now
    # represented by the on_behalf_of property of candidacy memberships:
    Membership.objects.filter(
        post__isnull=True,
        organization__classification='Party'
    ).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('candidates', '0008_membershipextra_organizationextra_personextra_postextra'),
        ('images', '0001_initial'),
        ('popolo', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(
            import_from_popit,
            lambda apps, schema_editor: None
        ),
    ]
