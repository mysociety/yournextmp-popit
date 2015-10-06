# What do the different user groups in YourNextRepresentative mean?

## Document Uploaders

Users in this group are allowed to upload official documents
that are associated with a post. This could be used, for
example, to upload PDF files of official nomination lists for
posts.

## Photo Reviewers

If you are in the 'Photo Reviewers' group, then you are allowed
to moderate uploaded images, and either approve or reject them.
If there are any photos for review, users in this group will see
a red box with the number of photos in the queues at the top of
each page. Clicking on that will take them to:

    /moderation/photo/review

... which shows the queue.

## Result Recorders

Users in this group get a "This candidate won!" button under
each candidate, which allows them to mark that candidate as
having been elected.

## Trusted To Lock

At some point in collecting data you may have enough confidence
in the list of candidates for a post that you want to 'lock' the
post. (For example, in the UK, we would do this after the
official nomination lists were published and the candidates for
a post had been hand-checked by a volunteer.) A user in the
'Trusted To Lock' group not only has the option to lock a post,
but may also continue to add and remove candidates from a post
even after the post is locked, to let them correct any mistakes
in the list that remain.

Note that the "locking" of a post only prevents candidates from
being added or removed from the list of candidates for that
post - all their details can still be edited.

## Trusted To Merge

If you find that a candidate has been added twice (or someone
added a new candidate when they were already in the database
from a previous election) it's a good idea to merge those two
people. Unfortunately, undoing an erroneous merge of two people
is very difficult, so it's a good idea to restrict the ability
to merge two candidates only to users who really know what
they're doing, and can be trusted to research properly whether
two people really are the same.

Only users in the 'Trusted to Merge' group will get the option
to merge two candidates on the candidate edit page.

## Trusted To Rename

One of the configuration options that you can enable in the
run-up to an election is `RESTRICT_RENAMES`. If this option is
enabled, then only users in the 'Trusted To Rename' group are
allowed to change the full name of a candidate. When someone not
in this group attempts to rename a candidate when
`RESTRICT_RENAMES` is true, an email describing the attempted
rename is sent to the support email address instead of the
rename taking effect.
