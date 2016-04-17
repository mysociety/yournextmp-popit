from __future__ import unicode_literals

from django.db import models

from popolo.models import Person

from compat import python_2_unicode_compatible


@python_2_unicode_compatible
class SimplePopoloField(models.Model):
    VALID_FIELDS = (
        ('name', 'Name'),
        ('family_name', 'Family Name'),
        ('given_name', 'Given Name'),
        ('additional_name', 'Additional Name'),
        ('honorific_prefix', 'Honorific Prefix'),
        ('honorific_suffix', 'Honorific Suffix'),
        ('patronymic_name', 'Patronymic Name'),
        ('sort_name', 'Sort Name'),
        ('email', 'Email'),
        ('gender', 'Gender'),
        ('birth_date', 'Birth Date'),
        ('death_date', 'Death Date'),
        ('summary', 'Summary'),
        ('biography', 'Biography'),
        ('national_identity', 'National Identity'),
    )

    name = models.CharField(
        choices=VALID_FIELDS,
        max_length=256
    )
    label = models.CharField(max_length=256)
    required = models.BooleanField(default=False)
    info_type_key = models.CharField(
        choices=(
            ('text', 'Text Field'),
            ('email', 'Email Field'),
        ),
        max_length=256
    )
    order = models.IntegerField(blank=True)

    def __str__(self):
        return self.name


@python_2_unicode_compatible
class ComplexPopoloField(models.Model):
    """
    This model stores the name of the underlying relation, some details about
    how it should be displayed ( label and field type ) and the details of
    how to store the information in the generic relation.

    The info_type_* properties are used to describe the key used to pull the
    field value out of the underlying generic relation. _key being the name
    of the field to store the value in info_type.

    info_value_key is the name of the field in the underlying relation in
    which to store the value of the complex field.

    To get the value for a person you fetch the item from the generic relation
    named in popolo_array where info_type_key matches info_type.
    """
    VALID_ARRAYS = (
        ('links', 'Links'),
        ('contact_details', 'Contact Details'),
        ('identifier', 'Identifier'),
    )

    name = models.CharField(
        max_length=256,
    )
    label = models.CharField(
        max_length=256,
        help_text="User facing description of the information",
    )
    popolo_array = models.CharField(
        choices=VALID_ARRAYS,
        max_length=256,
        help_text="Name of the Popolo related type",
    )

    field_type = models.CharField(
        choices=(
            ('text', 'Text Field'),
            ('url', 'URL Field'),
            ('email', 'Email Field'),
        ),
        max_length=256,
        help_text="Type of HTML field the user will see",
    )
    info_type_key = models.CharField(
        max_length=100,
        help_text="Name of the field in the array that stores the type ('note' for links, 'contact_type' for contacts, 'scheme' for identifiers)"
    )
    info_type = models.CharField(
        max_length=100,
        help_text="Value to put in the info_type_key e.g. twitter",
    )
    old_info_type = models.CharField(
        max_length=100,
        blank=True,
        help_text="Used for supporting info_types that have been renamed. As such it's rarely used."
    )
    info_value_key = models.CharField(
        max_length=100,
        help_text="Name of the field in the array that stores the value, e.g 'url' for links, 'value' for contact_type, 'identifier' for identifiers",
    )

    order = models.IntegerField(blank=True, default=0)

    def __str__(self):
        return self.name


@python_2_unicode_compatible
class ExtraField(models.Model):

    LINE = 'line'
    LONGER_TEXT = 'longer-text'
    URL = 'url'
    YESNO = 'yesno'

    FIELD_TYPES = (
        (LINE, 'A single line of text'),
        (LONGER_TEXT, 'One or more paragraphs of text'),
        (URL, 'A URL'),
        (YESNO, 'A Yes/No/Don\'t know dropdown')
    )

    key = models.CharField(max_length=256)
    type = models.CharField(
        max_length=64,
        choices=FIELD_TYPES,
    )
    label = models.CharField(max_length=1024)
    order = models.IntegerField(blank=True, default=0)

    def __str__(self):
        return self.key


class PersonExtraFieldValue(models.Model):

    class Meta:
        unique_together = (('person', 'field'))

    person = models.ForeignKey(Person, related_name='extra_field_values')
    field = models.ForeignKey(ExtraField)
    value = models.TextField(blank=True)
