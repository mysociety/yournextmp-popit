from django import forms, VERSION as django_version


if django_version[:2] < (1, 9):
    class StrippedCharField(forms.CharField):
        """A backport of the Django 1.9 ``CharField`` ``strip`` option.

        If ``strip`` is ``True`` (the default), leading and trailing
        whitespace is removed.
        """

        def __init__(self, max_length=None, min_length=None, strip=True,
                     *args, **kwargs):
            self.strip = strip
            super(StrippedCharField, self).__init__(max_length, min_length,
                                                    *args, **kwargs)

        def to_python(self, value):
            value = super(StrippedCharField, self).to_python(value)
            if self.strip:
                value = value.strip()
            return value
else:
    StrippedCharField = forms.CharField


class StrippedEmailField(forms.EmailField, StrippedCharField):
    pass


class StrippedURLField(forms.URLField, StrippedCharField):
    pass
