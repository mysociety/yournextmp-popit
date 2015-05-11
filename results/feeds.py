from django.contrib.syndication.views import Feed
from django.utils.feedgenerator import Atom1Feed

from .models import ResultEvent


class BasicResultEventsFeed(Feed):
    feed_type = Atom1Feed
    title = "Election results from YourNextMP"
    link = "/"
    description = "A basic feed of results from the UK 2015 General Election"

    def items(self):
        return ResultEvent.objects.all()

    def item_title(self, item):
        return u'{name} ({party}) won in {cons}'.format(
            name=item.winner_person_name,
            party=item.winner_party_name,
            cons=item.constituency_name,
        )

    def item_description(self, item):
        message = u'A YourNextMP volunteer recorded at {datetime} that ' \
            u'{name} ({party}) won the ballot in {cons}, quoting the ' \
            u"source '{source}'."
        return message.format(
            name=item.winner_person_name,
            datetime=item.created.strftime("%Y-%m-%d %H:%M:%S"),
            party=item.winner_party_name,
            cons=item.constituency_name,
            source=item.source,
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
            'winner_popit_person_id',
            'winner_person_name',
            'winner_party_id',
            'winner_party_name',
            'user_id',
            'constituency_name',
            'information_source',
        ]
        for k in [
            'image_url_template',
            'parlparse_id',
        ]:
            if item[k]:
                keys.append(k)
        for k in keys:
            handler.addQuickElement(k, unicode(item[k]))


class ResultEventsFeed(BasicResultEventsFeed):
    feed_type = ResultEventsAtomFeedGenerator
    title = "Election results from YourNextMP (with extra data)"
    description = "A feed of results from the UK 2015 General Election (with extra data)"

    def item_extra_kwargs(self, o):
        return {
            'post_id': o.post_id,
            'winner_popit_person_id': o.winner_popit_person_id,
            'winner_person_name': o.winner_person_name,
            'winner_party_id': o.winner_party_id,
            'winner_party_name': o.winner_party_name,
            'user_id': o.user.id,
            'user_id': o.user.id,
            'constituency_name': o.constituency_name,
            'information_source': o.source,
            'image_url_template': o.proxy_image_url_template,
            'parlparse_id': o.parlparse_id,
        }
