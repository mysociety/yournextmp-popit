from __future__ import unicode_literals

from django.contrib.auth.management import create_permissions


def get_migration_group_create(group_name, permission_codenames):

    def add_group_and_permissions(apps, schema_editor, create_if_missing=True):
        Permission = apps.get_model('auth', 'Permission')
        Group = apps.get_model('auth', 'Group')
        try:
            permissions = Permission.objects.filter(
                codename__in=permission_codenames
            )
        except Permission.DoesNotExist:
            if create_if_missing:
                # This is a way of making sure the permissions exist taken from:
                # https://code.djangoproject.com/ticket/23422#comment:6
                assert not getattr(apps, 'models_module', None)
                apps.models_module = True
                create_permissions(apps, verbosity=0)
                apps.models_module = None
                return add_group_and_permissions(
                    apps, schema_editor, create_if_missing=False
                )
            else:
                raise
        new_group = Group.objects.create(name=group_name)
        for permission in permissions:
            new_group.permissions.add(permission)

    return add_group_and_permissions

def get_migration_group_delete(group_name):

    def remove_group(apps, schema_editor):
        Group = apps.get_model('auth', 'Group')
        Group.objects.get(name=group_name).delete()

    return remove_group
