from __future__ import unicode_literals

import json

from rest_framework import serializers
from rest_framework.reverse import reverse
from sorl_thumbnail_serializer.fields import HyperlinkedSorlImageField

from candidates import models as candidates_models
from images.models import Image
from elections import models as election_models
from popolo import models as popolo_models

# These are serializer classes from the Django-REST-framework API
#
# For most objects there are two serializers - a full one and a
# minimal one.  The minimal ones (whose class names begin 'Minimal')
# are used for serializing the objects when they're just being
# included as related objects, rather than the resource that
# information is being requested about.
#
# e.g. if you request information about a Post via the 'posts'
# endpoint, it's pretty useful to have the ID, URL and name of the
# elections that the Post is part of, but you probably don't need
# every bit of election metadata.  A request to the 'elections'
# endpoint, however, would include full metadata about the elections.
#
# This reduces the bloat of API responses, at the cost of some users
# having to make extra queries.

class OtherNameSerializer(serializers.ModelSerializer):
    class Meta:
        model = popolo_models.OtherName
        fields = ('name', 'note')


class IdentifierSerializer(serializers.ModelSerializer):
    class Meta:
        model = popolo_models.Identifier
        fields = ('identifier', 'scheme')


class ContactDetailSerializer(serializers.ModelSerializer):
    class Meta:
        model = popolo_models.ContactDetail
        fields = ('contact_type', 'label', 'note', 'value')


class LinkSerializer(serializers.ModelSerializer):
    class Meta:
        model = popolo_models.Link
        fields = ('note', 'url')


class SourceSerializer(serializers.ModelSerializer):
    class Meta:
        model = popolo_models.Source
        fields = ('note', 'url')


class AreaTypeSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = election_models.AreaType
        fields = ('id', 'url',  'name', 'source')


class AreaSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = popolo_models.Area
        fields = (
            'id',
            'url',
            'name',
            'identifier',
            'classification',
            'other_identifiers',
            'parent',
            'type',
        )

    other_identifiers = IdentifierSerializer(many=True, read_only=True)
    type = AreaTypeSerializer(source='extra.type')


class ObjectWithImageField(serializers.RelatedField):

    def to_representation(self, value):
        kwargs = {'version': 'v0.9'}
        request = self.context['request']
        if isinstance(value, candidates_models.PersonExtra):
            kwargs.update({'pk': value.base.id})
            return reverse('person-detail', kwargs=kwargs, request=request)
        elif isinstance(value, candidates_models.OrganizationExtra):
            kwargs.update({'slug': value.slug})
            return reverse(
                'organizationextra-detail', kwargs=kwargs, request=request)
        elif isinstance(value, candidates_models.PostExtra):
            kwargs.update({'slug': value.slug})
            return reverse('postextra-detail', kwargs=kwargs, request=request)
        else:
            raise Exception("Unexpected type of object with an Image")


class ImageSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = Image
        fields = (
            'id',
            'url',
            'source',
            'is_primary',
            'md5sum',
            'copyright',
            'uploading_user',
            'user_notes',
            'user_copyright',
            'notes',
            'image_url',
            'content_object',
        )

    md5sum = serializers.ReadOnlyField(source='extra.md5sum')
    copyright = serializers.ReadOnlyField(source='extra.copyright')
    uploading_user = serializers.ReadOnlyField(source='extra.uploading_user.username')
    user_notes = serializers.ReadOnlyField(source='extra.user_notes')
    user_copyright = serializers.ReadOnlyField(source='extra.user_copyright')
    notes = serializers.ReadOnlyField(source='extra.notes')
    image_url = serializers.SerializerMethodField()
    content_object = ObjectWithImageField(read_only=True)

    def get_image_url(self, i):
        return i.image.url


class MinimalOrganizationExtraSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = candidates_models.OrganizationExtra
        fields = ('id', 'url', 'name')

    id = serializers.ReadOnlyField(source='slug')
    name = serializers.ReadOnlyField(source='base.name')
    url = serializers.HyperlinkedIdentityField(
        view_name='organizationextra-detail',
        lookup_field='slug',
        lookup_url_kwarg='slug',
    )


class PartySetSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = candidates_models.PartySet
        fields = ('id', 'url', 'name', 'slug')


class OrganizationExtraSerializer(MinimalOrganizationExtraSerializer):
    class Meta:
        model = candidates_models.OrganizationExtra
        fields = (
            'id',
            'url',
            'name',
            'other_names',
            'identifiers',
            'classification',
            'parent',
            'founding_date',
            'dissolution_date',
            'contact_details',
            'images',
            'links',
            'sources',
            'register',
            'party_sets',
        )

    classification = serializers.ReadOnlyField(source='base.classification')
    founding_date = serializers.ReadOnlyField(source='base.founding_date')
    dissolution_date = serializers.ReadOnlyField(source='base.dissolution_date')

    parent = MinimalOrganizationExtraSerializer(source='base.parent.extra')

    contact_details = ContactDetailSerializer(
        many=True, read_only=True, source='base.contact_details')
    identifiers = IdentifierSerializer(
        many=True, read_only=True, source='base.identifiers')
    links = LinkSerializer(
        many=True, read_only=True, source='base.links')
    other_names = OtherNameSerializer(
        many=True, read_only=True, source='base.other_names')
    sources = SourceSerializer(
        many=True, read_only=True, source='base.sources')
    images = ImageSerializer(many=True, read_only=True)

    party_sets = PartySetSerializer(
        many=True, read_only=True, source='base.party_sets')


class MinimalElectionSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = election_models.Election
        fields = ('id', 'url', 'name')

    id = serializers.ReadOnlyField(source='slug')
    url = serializers.HyperlinkedIdentityField(
        view_name='election-detail',
        lookup_field='slug',
        lookup_url_kwarg='slug',
    )


class ElectionSerializer(MinimalElectionSerializer):
    class Meta:
        model = election_models.Election
        fields = (
            'id',
            'url',
            'name',
            'for_post_role',
            'winner_membership_role',
            'candidate_membership_role',
            'election_date',
            'current',
            'use_for_candidate_suggestions',
            'area_types',
            'area_generation',
            'organization',
            'party_lists_in_use',
            'default_party_list_members_to_show',
            'show_official_documents',
            'ocd_division',
            'description'
        )


    organization = MinimalOrganizationExtraSerializer(source='organization.extra')

    area_types = AreaTypeSerializer(many=True, read_only=True)


class MinimalPostExtraSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = candidates_models.PostExtra
        fields = ('id', 'url', 'label', 'slug')

    id = serializers.ReadOnlyField(source='slug')
    label = serializers.ReadOnlyField(source='base.label')
    url = serializers.HyperlinkedIdentityField(
        view_name='postextra-detail',
        lookup_field='slug',
        lookup_url_kwarg='slug',
    )


class MinimalPersonSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = popolo_models.Person
        fields = ('id', 'url', 'name')


class MembershipSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = popolo_models.Membership
        fields = (
            'id',
            'url',
            'label',
            'role',
            'elected',
            'party_list_position',
            'person',
            'organization',
            'on_behalf_of',
            'post',
            'start_date',
            'end_date',
            'election',
        )

    elected = serializers.ReadOnlyField(source='extra.elected')
    party_list_position = serializers.ReadOnlyField(
        source='extra.party_list_position')
    person = MinimalPersonSerializer(read_only=True)
    organization = MinimalOrganizationExtraSerializer(
        read_only=True, source='organization.extra')
    on_behalf_of = MinimalOrganizationExtraSerializer(
        read_only=True, source='on_behalf_of.extra')
    post = MinimalPostExtraSerializer(
        read_only=True, source='post.extra')

    election = MinimalElectionSerializer(source='extra.election')


class PostElectionSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = candidates_models.PostExtraElection
        fields = ('id', 'url', 'post', 'election', 'winner_count')
    post = MinimalPostExtraSerializer(
        read_only=True, source='postextra'
    )
    election = MinimalElectionSerializer(read_only=True)


class JSONSerializerField(serializers.Field):
    def to_representation(self, value):
        return json.loads(value)


class PersonExtraFieldSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = candidates_models.PersonExtraFieldValue
        fields = ('key', 'value', 'type')

    key = serializers.ReadOnlyField(source='field.key')
    type = serializers.ReadOnlyField(source='field.type')


class PersonSerializer(MinimalPersonSerializer):
    class Meta:
        model = popolo_models.Person
        fields = (
            'id',
            'url',
            'name',
            'other_names',
            'identifiers',
            'honorific_prefix',
            'honorific_suffix',
            'sort_name',
            'email',
            'gender',
            'birth_date',
            'death_date',
            'versions',
            'contact_details',
            'links',
            'memberships',
            'images',
            'extra_fields',
            'thumbnail',
            'marked_for_review',
        )

    contact_details = ContactDetailSerializer(many=True, read_only=True)
    identifiers = IdentifierSerializer(many=True, read_only=True)
    links = LinkSerializer(many=True, read_only=True)
    other_names = OtherNameSerializer(many=True, read_only=True)
    images = ImageSerializer(many=True, read_only=True, source='extra.images')

    marked_for_review = serializers.ReadOnlyField(source='extra.marked_for_review')
    versions = JSONSerializerField(source='extra.versions', read_only=True)

    memberships = MembershipSerializer(many=True, read_only=True)

    extra_fields = PersonExtraFieldSerializer(
        many=True, read_only=True, source='extra_field_values')

    thumbnail = HyperlinkedSorlImageField(
            '300x300',
            options={"crop": "center"},
            source='extra.primary_image',
            read_only=True
        )

class PostExtraSerializer(MinimalPostExtraSerializer):
    class Meta:
        model = candidates_models.PostExtra
        fields = (
            'id',
            'url',
            'label',
            'role',
            'group',
            'candidates_locked',
            'party_set',
            'organization',
            'area',
            'elections',
            'memberships',
        )

    role = serializers.ReadOnlyField(source='base.role')
    party_set = PartySetSerializer(read_only=True)
    area = AreaSerializer(source='base.area')

    memberships = MembershipSerializer(
        many=True, read_only=True, source='base.memberships')

    organization = MinimalOrganizationExtraSerializer(
        source='base.organization.extra')

    elections = MinimalElectionSerializer(many=True, read_only=True)


class LoggedActionSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = candidates_models.LoggedAction
        fields = (
            'id',
            'url',
            'user',
            'person',
            'action_type',
            'person_new_version',
            'created',
            'updated',
            'source'
        )

    person_new_version = serializers.ReadOnlyField(
        source='popit_person_new_version')
    user = serializers.ReadOnlyField(source='user.username')
    person = MinimalPersonSerializer(read_only=True)


class ExtraFieldSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = candidates_models.ExtraField
        fields = ('id', 'url', 'key', 'type', 'label', 'order')


class SimplePopoloFieldSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = candidates_models.SimplePopoloField
        fields = (
            'id', 'url', 'name', 'label', 'required', 'info_type_key', 'order'
        )


class ComplexPopoloFieldSerializer(serializers. HyperlinkedModelSerializer):
    class Meta:
        model = candidates_models.ComplexPopoloField
        fields = (
            'id', 'url', 'name', 'label', 'popolo_array', 'field_type',
            'info_type_key', 'info_type', 'old_info_type', 'info_value_key',
            'order',
        )


class PersonRedirectSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = candidates_models.PersonRedirect
        fields = ('id', 'url', 'old_person_id', 'new_person_id')

    url = serializers.HyperlinkedIdentityField(
        view_name='personredirect-detail',
        lookup_field='old_person_id',
        lookup_url_kwarg='old_person_id',
    )
