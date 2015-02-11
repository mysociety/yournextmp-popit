from django.contrib import admin
from .models import QueuedImage

class QueuedImageAdmin(admin.ModelAdmin):
    list_display = ('user', 'popit_person_id', 'created', 'decision')
    ordering = ('-created',)

admin.site.register(QueuedImage, QueuedImageAdmin)
