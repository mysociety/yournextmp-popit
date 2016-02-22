from __future__ import unicode_literals

from django.contrib import admin

from django.core.urlresolvers import reverse
from django.forms import ModelForm

from .models import (
    LoggedAction, PartySet, ExtraField, PersonExtraFieldValue,
    SimplePopoloField, ComplexPopoloField
)
# Register your models here.


class LoggedActionAdminForm(ModelForm):
    pass


class LoggedActionAdmin(admin.ModelAdmin):
    form = LoggedActionAdminForm
    search_fields = ('user__username', 'popit_person_new_version',
                     'person', 'ip_address', 'source')
    list_filter = ('action_type',)
    list_display = ['user', 'ip_address', 'action_type',
                    'popit_person_new_version', 'person_link',
                    'created', 'updated', 'source']
    ordering = ('-created',)

    def person_link(self, o):
        if not o.person:
            return ''
        url = reverse('person-view', kwargs={'person_id': o.person.id})
        return '<a href="{0}">{1}</a>'.format(
            url,
            o.person.name,
        )
    person_link.allow_tags = True


class PartySetAdminForm(ModelForm):
    pass


class PartySetAdmin(admin.ModelAdmin):
    form = PartySetAdminForm


class ExtraFieldAdminForm(ModelForm):
    pass


class ExtraFieldAdmin(admin.ModelAdmin):
    form = ExtraFieldAdminForm


class PersonExtraFieldValueAdminForm(ModelForm):
    pass


class PersonExtraFieldValueAdmin(admin.ModelAdmin):
    form = PersonExtraFieldValueAdminForm


class SimplePopoloFieldAdmin(admin.ModelAdmin):
    list_display = ['name', 'label']


class ComplexPopoloFieldAdmin(admin.ModelAdmin):
    list_display = ['name', 'label']


admin.site.register(LoggedAction, LoggedActionAdmin)
admin.site.register(PartySet, PartySetAdmin)
admin.site.register(ExtraField, ExtraFieldAdmin)
admin.site.register(PersonExtraFieldValue, PersonExtraFieldValueAdmin)
admin.site.register(SimplePopoloField, SimplePopoloFieldAdmin)
admin.site.register(ComplexPopoloField, ComplexPopoloFieldAdmin)
