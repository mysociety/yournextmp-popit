from __future__ import unicode_literals

from django.contrib import admin
from .models import QueuedImage

class QueuedImageAdmin(admin.ModelAdmin):
    list_display = ('user', 'person', 'created', 'decision')
    search_fields = ('user__username', 'person__id')
    list_filter = ('decision',)
    ordering = ('-created',)

admin.site.register(QueuedImage, QueuedImageAdmin)
