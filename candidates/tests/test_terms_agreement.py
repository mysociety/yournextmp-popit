from __future__ import unicode_literals

from django.test import TestCase

from django.contrib.auth.models import User

class Test(TestCase):

    def test_user_creation_creates_terms_agreement(self):
        u = User.objects.create_user(
            'john',
            'john@example.com',
            'notagoodpassword',
        )
        self.assertFalse(u.terms_agreement.assigned_to_dc)
