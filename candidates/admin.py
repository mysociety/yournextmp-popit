from django.contrib import admin

from django.core.urlresolvers import reverse
from django.forms import ModelForm

from .models import LoggedAction
# Register your models here.

class LoggedActionAdminForm(ModelForm):
    pass

class LoggedActionAdmin(admin.ModelAdmin):
    form = LoggedActionAdminForm
    search_fields = ('user__username', 'popit_person_new_version',
                     'popit_person_id', 'ip_address', 'source')
    list_filter = ('action_type',)
    list_display = ['user', 'ip_address', 'action_type',
                    'popit_person_new_version', 'popit_person_link',
                    'created', 'updated', 'source']
    ordering = ('-created',)

    def popit_person_link(self, o):
        if not o.popit_person_id:
            return ''
        url = reverse('person-view', kwargs={'person_id': o.popit_person_id})
        return '<a href="{0}">{1}</a>'.format(
            url,
            o.popit_person_id,
        )
    popit_person_link.allow_tags = True

admin.site.register(LoggedAction, LoggedActionAdmin)
