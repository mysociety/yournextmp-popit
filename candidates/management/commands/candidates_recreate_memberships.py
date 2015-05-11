# From (I believe) historical bugs, some candidates are missing PopIt
# memberships.  This command will recreate them based on their
# standing_in and party_memberships data.
#
#   e.g. ./manage.py candidates_recreate_memberships 2825 3411

from django.core.management.base import BaseCommand, CommandError

from candidates.cache import invalidate_posts, invalidate_person
from candidates.models import PopItPerson
from candidates.popit import create_popit_api_object, PopItApiMixin

class Command(PopItApiMixin, BaseCommand):

    args = "<PERSON-ID> ..."
    help = "Recreate one or more person's memberships (for fixing bad data)"

    def handle(self, *args, **kwargs):
        api = create_popit_api_object()
        if len(args) < 1:
            raise CommandError("You must provide one or more PopIt person ID")
        for person_id in args:
            invalidate_person(person_id)
            person = PopItPerson.create_from_popit(api, person_id)
            posts_to_invalidate = person.get_associated_posts()
            person.delete_memberships(api)
            # The memberships are recreated when you assign to
            # standing_in and party_memberships; this script assumes
            # these are correct and so re-setting these should
            # recreate the memberships correctly.
            person.standing_in = person.standing_in
            person.party_memberships = person.party_memberships
            person.save_to_popit(api)
            invalidate_posts(posts_to_invalidate)
            invalidate_person(person_id)
