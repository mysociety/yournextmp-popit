from django.contrib.auth.models import User, Group

from candidates.models import (
    TRUSTED_TO_MERGE_GROUP_NAME,
    TRUSTED_TO_LOCK_GROUP_NAME,
    TRUSTED_TO_RENAME_GROUP_NAME,
    RESULT_RECORDERS_GROUP_NAME,
)
from official_documents.models import DOCUMENT_UPLOADERS_GROUP_NAME

class TestUserMixin(object):

    @classmethod
    def setUpClass(cls):
        cls.users_to_delete = []
        for username, attr, group_names in (
                ('john', 'user', []),
                ('alice', 'user_who_can_merge', [TRUSTED_TO_MERGE_GROUP_NAME]),
                ('charles', 'user_who_can_lock', [TRUSTED_TO_LOCK_GROUP_NAME]),
                ('delilah', 'user_who_can_upload_documents', [DOCUMENT_UPLOADERS_GROUP_NAME]),
                ('ermintrude', 'user_who_can_rename', [TRUSTED_TO_RENAME_GROUP_NAME]),
                ('frankie', 'user_who_can_record_results', [RESULT_RECORDERS_GROUP_NAME]),
        ):
            u = User.objects.create_user(
                username,
                username + '@example.com',
                'notagoodpassword',
            )
            terms = u.terms_agreement
            terms.assigned_to_dc = True
            terms.save()
            for group_name in group_names:
                group = Group.objects.get(name=group_name)
                group.user_set.add(u)
            setattr(cls, attr, u)
            cls.users_to_delete.append(u)
        # Also add a user who hasn't accepted the terms, and isn't in
        # any groups:
        cls.user_refused = User.objects.create_user(
            'johnrefused',
            'johnrefused@example.com',
            'notagoodpasswordeither',
        )
        cls.users_to_delete.append(cls.user_refused)

    @classmethod
    def tearDownClass(cls):
        for u in cls.users_to_delete:
            u.delete()
