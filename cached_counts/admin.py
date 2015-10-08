from cached_counts.models import CachedCount
from django.contrib import admin

class CachedCountAdmin(admin.ModelAdmin):
    #list of editable fields
    fields = ['count_type', 'name','count','object_id','election','election_dateA']
    list_display = ('count_type', 'name','count','object_id','election','election_dateA')
    list_filter = ['count_type']
admin.site.register(CachedCount, CachedCountAdmin)
