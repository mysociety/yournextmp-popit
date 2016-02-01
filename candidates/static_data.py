from __future__ import unicode_literals

from collections import defaultdict

from django.utils.translation import ugettext as _

from elections.models import Election


class BaseAreaPostData(object):

    """Instantiate this class to provide mappings between areas and posts

    FIXME: check that these are sensible descriptions

    If you instantiate this class you will get the following attributes:

         'area_ids_and_names_by_post_group', maps a post group to a
         list of all areas of a particular type

         'areas_by_post_id', maps a post ID to all areas associated
         with it
    """

    def area_to_post_group(self, area_data):
        raise NotImplementedError(
            "You should implement area_to_post_group in a subclass"
        )

    def get_post_id(self, election, area_type, area_id):
        return Election.objects.get_by_slug(election).post_id_format.format(
            area_id=area_id
        )

    def __init__(self, area_data):
        self.area_data = area_data
        self.areas_by_post_id = {}
        self.area_ids_and_names_by_post_group = {}

        for area_tuple, election_tuples in Election.objects.elections_for_area_generations().items():
            for election_data in election_tuples:
                area_type, area_generation = area_tuple
                for area in self.area_data.areas_by_id[area_tuple].values():
                    post_id = self.get_post_id(election_data.slug, area_type, area['id'])
                    if post_id in self.areas_by_post_id:
                        message = _("Found multiple areas for the post ID {post_id}")
                        raise Exception(message.format(post_id=post_id))
                    self.areas_by_post_id[post_id] = area
                for area in area_data.areas_by_name[area_tuple].values():
                    post_group = self.area_to_post_group(area)
                    self.area_ids_and_names_by_post_group.setdefault(area_tuple, defaultdict(list))
                    self.area_ids_and_names_by_post_group[area_tuple][post_group].append(
                        (str(area['id']), area['name'])
                    )
                for area_list in self.area_ids_and_names_by_post_group[area_tuple].values():
                    area_list.sort(key=lambda c: c[1])
