from django.contrib import admin
from django.core.urlresolvers import reverse
from django.utils.text import slugify
from .models import ResultEvent

class ResultEventAdmin(admin.ModelAdmin):
    list_display = (
        'user',
        'created',
        'winner_popit_person_id',
        'person_link',
        'winner_party_id',
        'winner_party_name',
        'post_id',
        'post_name',
        'constituency_link',
        'source',
    )
    search_fields = (
        'user__username',
        'winner_popit_person_id',
        'winner_person_name',
        'winner_party_id',
        'post_id',
        'post_name',
        'source',
    )
    ordering = ('-created',)

    def person_link(self, o):
        url = reverse(
            'person-view',
            kwargs={
                'person_id': o.winner_popit_person_id,
                'ignored_slug': slugify(o.post_name),
            }
        )
        return '<a href="{0}">{1}</a>'.format(
            url,
            o.winner_person_name,
        )
    person_link.allow_tags = True

    def constituency_link(self, o):
        url = reverse(
            'constituency',
            kwargs={
                'post_id': o.post_id,
                'ignored_slug': slugify(o.post_name),
            }
        )
        return '<a href="{0}">{1}</a>'.format(
            url,
            o.post_name,
        )
    constituency_link.allow_tags = True

admin.site.register(ResultEvent, ResultEventAdmin)
