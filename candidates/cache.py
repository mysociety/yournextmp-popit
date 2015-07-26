from django.core.cache import cache
from django.utils.text import slugify

from slumber.exceptions import HttpClientError

from .popit import get_all_posts


class UnknownPostException(Exception):
    pass


def post_cache_key(post_id):
    """Form the cache key used for post data"""
    return "post:{0}".format(post_id)

def person_cache_key(person_id):
    """Form the cache key used for person data"""
    return "person:{0}".format(person_id)

def invalidate_posts(post_ids):
    """Delete cache entries for all of these PopIt posts"""
    cache.delete_many(post_cache_key(post_id) for post_id in post_ids)

def invalidate_person(person_id):
    """Delete the cache entry for a particular person's PopIt data"""
    person_key = person_cache_key(person_id)
    cache.delete(person_key)

def get_post_cached(api, post_id):
    post_key = post_cache_key(post_id)
    result_from_cache = cache.get(post_key)
    if result_from_cache is not None:
        return result_from_cache

    try:
        mp_post = api.posts(post_id).get(
            embed='membership.person.membership.organization')
    except HttpClientError as hce:
        # Disappointingly, slumber doesn't seem to store the response
        # status code on the HttpClientError exception, so just look
        # for the expected message content:
        if 'not found' in hce.content:
            raise UnknownPostException()
        raise
    # Add posts data with an indefinite time-out (we should be
    # invalidating the cached on any change).
    cache.set(post_key, mp_post, None)

    return mp_post

def get_person_cached(api, person_id):
    person_key = person_cache_key(person_id)
    result_from_cache = cache.get(person_key)
    if result_from_cache is not None:
        return result_from_cache
    person_data = api.persons(person_id).get(
            embed='membership.organization'
    )
    # Add it the person data to the cache with a timeout of
    # a day.
    cache.set(person_key, person_data, 86400)
    return person_data

def get_all_posts_cached(api, role):
    posts_key = 'posts-no-embed-with-role-' + slugify(unicode(role))
    result_from_cache = cache.get(posts_key)
    if result_from_cache is not None:
        return result_from_cache
    all_post_data = sorted(
        get_all_posts(role),
        key=lambda post: post['label'],
    )
    cache.set(posts_key, all_post_data, 86400)
    return all_post_data
