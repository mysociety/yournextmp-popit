# Working with Transifex

This is a short guide to both:

* Getting new translations from Transifex
* Uploading new strings for translation to Transifex

Make sure that you have the latest Transifex client installed in
your virtualenv with:

```
pip install transifex
```

Make sure that `git status` is clean before you start.

Firstly, pull the most recent translations for Transifex:

```
tx pull -a -f
```

If you've already run `makemessages`, that may delete messages
from the `.po` files, but don't worry about that because we're going to
run `makemessages` later and that'll put them back.

Now look through the changes with `git diff locale` to check for
anything broken or malicious (e.g. people sometimes mistakenly
translated the identifiers in format specifiers).

Assuming that's fine, commit those changes, since when we later
push back the new set of strings for translation, any that have
disappeared will be deleted from Transifex too.  Committing
after pulling from Transifex should at least mean we've recorded
all the translations that have been done before this
update. (Transifex doesn't have any version control that would
record these.)

```
git commit -m "Recording the latest translations from Transifex" locale
```

Now update the `.po` files with any new strings that have been
added to the project with:

```
./manage.py makemessages -a \
    --ignore=data --ignore=candidates/static/foundation
```

That will add some fuzzily inferred translations to the `.po`
files, but they won't be added to Transifex when we upload
(since it doesn't support fuzzy translations) and later we'll
pull back from transifex to remove them.

If there are any new strings for translation, you should be able
to see them from `git diff`.

Now push those new strings to Transifex with:

```
tx push -s -t --skip
```

Now if you pull from Transifex again, that should remove the fuzzy translations:

```
tx pull -a -f
```

Now you can commit the result:

```
git commit -m "Updated .po files from makemessages, without fuzzy translations" locale
```

And run:

```
./manage.py compilemessages
```

---

n.b. These instructions are based on those from
[Alavetli](https://github.com/mysociety/alaveteli/wiki/Release-Manager's-checklist),
with thanks.
