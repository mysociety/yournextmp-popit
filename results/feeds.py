from __future__ import unicode_literals

from django.contrib.sites.models import Site
from django.contrib.syndication.views import Feed
from django.utils.feedgenerator import Atom1Feed
from django.utils.translation import ugettext_lazy as _

from compat import text_type

from .models import ResultEvent


class BasicResultEventsFeed(Feed):
    feed_type = Atom1Feed
    title = _("Election results from {site_name}").format(
        site_name=Site.objects.get_current().name
    )
    link = "/"
    description = _("A basic feed of election results")

    def items(self):
        return ResultEvent.objects.all()

    def item_title(self, item):
        return _('{name} ({party}) won in {cons}').format(
            name=item.winner_person_name,
            party=item.winner_party_name,
            cons=item.post_name,
        )

    def item_description(self, item):
        message = _('A {site_name} volunteer recorded at {datetime} that '
            '{name} ({party}) won the ballot in {cons}, quoting the '
            "source '{source}').")
        return message.format(
            name=item.winner_person_name,
            datetime=item.created.strftime("%Y-%m-%d %H:%M:%S"),
            party=item.winner_party_name,
            cons=item.post_name,
            source=item.source,
            site_name=Site.objects.get_current().name,
        )

    def item_link(self, item):
        # Assuming we're only going to show these events on the front
        # page for the moment:
        return '/#{0}'.format(item.id)

    def item_updateddate(self, item):
        return item.created

    def item_pubdate(self, item):
        return item.created

    def item_author_name(self, item):
        if item.user:
            return item.user.username
        return "unknown"


class ResultEventsAtomFeedGenerator(Atom1Feed):

    def add_item_elements(self, handler, item):
        super(ResultEventsAtomFeedGenerator, self). \
            add_item_elements(handler, item)
        keys = [
            'post_id',
            'winner_person_id',
            'winner_person_name',
            'winner_party_id',
            'winner_party_name',
            'user_id',
            'post_name',
            'information_source',
        ]
        for k in [
            'image_url_template',
            'parlparse_id',
        ]:
            if item[k]:
                keys.append(k)
        for k in keys:
            handler.addQuickElement(k, text_type(item[k]))


class ResultEventsFeed(BasicResultEventsFeed):
    feed_type = ResultEventsAtomFeedGenerator
    title = _("Election results from {site_name} (with extra data)").format(
        site_name=Site.objects.get_current().name
    )
    description = _("A feed of results from the UK 2015 General Election (with extra data)")

    def item_extra_kwargs(self, o):
        return {
            'post_id': o.post_id,
            'winner_person_id': o.winner.id,
            'winner_person_name': o.winner.name,
            'winner_party_id': o.winner_party_id,
            'winner_party_name': o.winner_party_name,
            'user_id': o.user.id,
            'user_id': o.user.id,
            'post_name': o.post_name,
            'information_source': o.source,
            'image_url_template': o.proxy_image_url_template,
            'parlparse_id': o.parlparse_id,
        }
