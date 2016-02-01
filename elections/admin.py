from __future__ import unicode_literals

from django.contrib import admin
from .models import AreaType, Election

class ElectionAdmin(admin.ModelAdmin):
    list_display = ('name', 'description', 'current')
    search_fields = ('name', 'slug')
    ordering = ('election_date', 'name')

class AreaTypeAdmin(admin.ModelAdmin):
    list_display = ('name', 'source')
    search_fields = ('name', 'source')

admin.site.register(Election, ElectionAdmin)
admin.site.register(AreaType, AreaTypeAdmin)
