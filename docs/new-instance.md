# Making a new instance of YourNextRepresentative

## Introduction

This document is a work-in-progress. You'll need to have
experience of developing in Python, and ideally working on
Django projects, for this to make much sense. We're aware that
this should all much simpler to do, and are actively working on
improving that!

## Preliminaries

We've seen that the most important things in creating a
successful new YourNextRepresentative site are:

* Having a clear understanding of the electoral system in the
  country or jurisdiction you're setting up the site for.
* Choosing a realistic set of candidates that you want to
  crowd-source - not being too ambitious!
* Having a core community of moderators who are happy to check
  all the recent changes and follow-up by email with anyone
  making badly sourced edits.
* Giving us early feedback (to <ynr@mysociety.org>) when you
  encounter any problems or bugs - this is still alpha software!

## Components of a YourNextRepresentative site

To broadly introduce the architecture of YourNextRepresentative
(YNR), these are the main bits of software that the site
requires to run:

* [yournextrepresentative](https://github.com/mysociety/yournextrepresentative/) -
  the Django application in this repository, which is the
  web-based front-end for editing candidate data.
* [Memcached](http://memcached.org/) - this is used for caching
  some API results from PopIt and MapIt.
* [PopIt](http://popit.poplus.org/) - a data store for
  information about people and organizations, which is
  accessible over a RESTful API. This is where the data about
  candidates is stored.
* [MapIt](http://mapit.poplus.org/) - MapIt provides an API
  for, among other things, looking up an administrative boundary
  from a longitude / latitude or a postcode. If you want to have
  an address box on the front page of your YNR site, which will
  let users look up the candidates relevant for where they live,
  you will need an instance of MapIt.
* [Varnish](https://www.varnish-cache.org/) - if your site is
  getting enough traffic that performance is poor, we recommend
  using Varnish as a caching reverse proxy in front of
  yournextrepresentative.

## Requirements

The next sections of this document go into more detail about
the components of the site and other data that you will need in
order to set up the site.

### A PopIt instance to store candidate data

(We are in the process of deprecating the use of PopIt as a
backend for YNR, but for the moment this is still the only
supported way to set up a site.)

#### Using mySociety's hosted PopIt service

If you don't have a user account on http://popit.mysociety.org,
then you'll need to
[create one](https://popit.mysociety.org/register). Then you can
[create a new PopIt instance](https://popit.mysociety.org/instances/new).

It's generally a good idea to create a separate PopIt instance
to use for testing your staging site out as well.  You can use
the corresponding links on http://popit.staging.mysociety.org/
to do that.

#### Setting up your own PopIt site

Setting up your own PopIt site involves more work, but you might
need to do that if the network latency between mySociety's PopIt
installantion and where you're hosting
yournextrepresentative. There is guidance on installing your own
PopIt site here: http://popit.poplus.org/docs/install/

### Create a list of political parties in Popolo JSON

YNR has a strong assumption that there is a fixed list of
political parties that candidates may be standing for. (n.b. the
list of parties can be different in different geographical
areas - for this more advanced feature see the description of
"Party Sets" below).

We recommend that you create a
[Popolo JSON file](http://www.popoloproject.com/) with all the
political parties that candidates might stand for. This is used
for the party options shown in drop-down lists in the site's
interface. There is a Django admin command called
`candidates_create_popit_organizations` you can use to create
the corresponding party organizations in PopIt based on this
JSON file. The IDs of the parties in the JSON file should be
stable (ideally some official ID if such exists) so that
re-running this command will update the parties in PopIt without
creating duplicates.

For examples of such Popolo JSON files of political parties, you
can look at those for the UK and Argentina:

* https://github.com/mysociety/yournextrepresentative/blob/master/elections/uk_general_election_2015/data/all-parties-from-popit.json
* https://github.com/mysociety/yournextrepresentative/blob/master/elections/ar_elections_2015/data/all-parties-from-popit.json

### MapIt

If candidates in your electoral system are associated with
geographical constituencies, and you wish to have geographic
lookup of candidates so that users can easily find candidates
relevant to them, you will need an instance of MapIt that
contains the boundaries of those constituencies. There are
various options you have here:

* If OpenStreetMap has the administrative boundaries you need,
  they will be in
  [MapIt: Global](http://global.mapit.mysociety.org/).
  (Note that this currently isn't as easy to use as it should be
  in YNR - there are more details here:  https://github.com/mysociety/yournextrepresentative/issues/507)

* If you have access to shapefiles for those boundaries
  (e.g. from an official source like a mapping agency) then you
  have two options:
  * You can
    [set up your own MapIt](http://mapit.poplus.org/docs/self-hosted/)
    and import those boundaries.
  * You can [ask us](mailto:ynr@mysociety.org) to import the
    boundaries into our MapIt instance for boundaries whose
    licensing isn't compatible with OpenStreetMap.

### Define the elections you're collecting candidates for

You will need to add a new Django application in the `elections`
package - you can use `uk_general_election_2015` as an
example. You should then set `ELECTION_APP` in your
`general.yml` to the name of that application (not including
`elections.`).

In this new application you will need to do the following:

* Create a `settings` module which defines an `ELECTIONS`
  dictionary. (The details of the meaning of these fields are
  described just below.)

* Override generic templates in your election application.

* Optionally add a `urls.py` and `views.py` to override and
  augment and of the generic URLs that you want to customize.

* Some data and behaviour will need to be customized by adding
  functions or variables in `lib.py` in your election application.

#### The `ELECTIONS` dictionary in `settings.py`

(It may be useful to look at the existing `settings.py` files
for
[Argentina](https://github.com/mysociety/yournextrepresentative/blob/master/elections/ar_elections_2015/settings.py)
and
[the UK](https://github.com/mysociety/yournextrepresentative/blob/master/elections/uk_general_election_2015/settings.py)
as examples.)

Each key in the `ELECTIONS` dictionary will be used as the slug
to refer to that election in URLs on the site (e.g. in the UK
these are `2010` and `2015`). The value for each of these should
be a dictionary with keys and values containing data about that
election. The meaning of these keys is as follows:

`for_post_role` - this is the name of the Post that the
candidates in this election are trying to get elected to
(e.g. 'Member of Parliament')

`candidate_membership_role` - this is normally just 'Candidate',
unless this is a primary election, in which case you'd use
'Primary Candidate'.  This is used when the code is looking for
Memberships of the Post that represent people standing as a
candidate for that Post.

`winner_membership_role` - once the election is over, users in
the 'Result Recorders' group can click on a button that says
"This candidate won!".  If that's used, then a new Membership of
the Post will be created for that candidate with the role given
by this setting.  Normally that will just be None, meaning that
the Membership should have no role specified - the default
interpretation of a Membership of a role is that that person is
fulfilling that role. However, in a primary election, the role
that will be created for the winner might be `Candidate`.

`election_date` - a Python `datetime.date` object indicating the
day on which votes are cast in the election.

`candidacy_start_date` - When someone is added as a candidate, a
Membership of that Post (typically with role 'Candidate') is
created. `candidacy_start_date` is a Python `datetime.date` that
describes when the `start_date` of that Membership should be.
It's a bit artificial to make this the same for all candidates
in the election, but in the countries we've used the code in so
far it has been rare to actually know the date when someone
becomes a candidate, and having a `start_date` on these
Memberships makes certain queries against the PopIt API that use
date ranges work properly. We normally set this date to the day
after the previous election.

`organization_id` - This is the ID of the Organization that the
candidates would be serving in if they are elected.  e.g. in
the UK elections this would be "House of Commons"

`name` - This is the name of the election, as it would be
normally described. This shouldn't be prefixed with 'The',
since most of the uses of the election name on the site prefix
it with a 'The' anyway.  For example, this value might be '2015
General Election'

`current` - This is a boolean value indicating if this election
and candidates from it should be shown on various pages.

`use_for_candidate_suggestions` - If this is set to True, then on
the page for a Post, the candidates from this election will be
offered as possibile candidates for this election in an "Are
these candidates standing again?" section, so you can quickly
say "Yes, they are" or "No, they aren't".

`party_membership_start_date` / `party_membership_end_date` - These
are similar to `candidacy_start_date` in being rather artificial;
these are the start and end dates of party Memberships that are
created when you set the party that a candidate is standing
for.  We usually (artificially) set the `start_date` to the day
after the previous election of the same type and the `end_date`
to `date(9999, 12, 31)` for current elections.

`mapit_types` - a list of 3-letter MapIt type codes for the
types of area that these Posts might be associated with.

`mapit_generation` - the ID of the MapIt generation that the
areas that these Posts might be associated with are from.

`post_id_format` - this is a Python format string that is used to
find the ID of the Post in this election for a particular
area. If you include `{area_id}` then that will be replaced by
the area ID.

### Creating Posts in PopIt

YNR uses the Popolo data model, and in particular its concept of
'Posts' to represent the structure of an election.  A 'Post'
will be something like 'Member of Parliament for Cambridge'.  A
Person who is a candidate will then have a Membership of the
Post, with the role 'Candidate' as an attribute of the
Membership.  For example, here are all the posts created for the
elections in Argentina, grouped by election:

  http://investigacion.yoquierosaber.org/posts

If all the Posts that you need to create are associated with
areas in MapIt, it should be possible, once the MapIt instance
is created and the ELECTIONS data structure in
`elections/*/settings.py` has been created, to create those
posts with the admin command `candidates_create_popit_posts`.

### Translation and localization

We use [Transifex](https://www.transifex.com/) as the interface
for authoring translations of the site, so that teams of
volunteers can collaborate on creating the translations. If you
want to contribute translations, you should go to:
https://www.transifex.com/mysociety/yournextmp/

(Note that for pages like the "About" page or "Copyright
Assignment" page, which are essentially lots of static text that
will need to be completely different for each site, it's best to
create a new template in your elections application which
overrides the default.)

If you want to take the updated translations from Transifex and
commit them into the codebase, you should follow the
instructions in [docs/transifex.md](transifex.md)

### Programmatically importing candidates

It's frequently the case that some lists of candidates, however
incomplete, may be available, and it can be useful to see your
YNR site with these candidates.

This should be done with a Django management command using the
`PopItPerson` model to make sure that they're created with all
the right data attributes, and an initial version history.  As a
model, you can look at
[this code](https://github.com/mysociety/yournextrepresentative/blob/master/elections/ar_elections_2015/management/commands/ar_elections_2015_import_candidates.py#L170-L215),
for example.

### Deployment

YNR is a fairly standard Django site, so hopefully its
deployment shouldn't be too difficult if you have previous
experience of deploying Django sites.  In the past we have used
Apache / mod_wsgi and nginx / uwsgi for deployment, and other
application servers like gunicorn should work fine.  You'll need
to have memcached installed on the server as well.  We made a
short checklist for Argentina of other things to look out for
when deploying, which you can find here:
https://github.com/mysociety/yournextrepresentative/issues/417

### Further customizations

You will also have to decide if you you want to create "party
sets" or "post groups" for the elections you're supporting.
These are potentially confusing, so here are some quick
descriptions:

#### Party Sets

It's sometimes the case that there are different sets of parties
available for different posts that are up for election.  (For
example, in the UK General Election, there are distinct
registers of parties for constituencies in Northern Ireland and
Great Britain.)

To create multiple party sets, you must subclass two
classes. This should be done in `elections/*/lib.py`:

1. Create a class `PartyData`, inheriting from
   `BasePartyData`. In its `__init__` method it should, after
   calling the superclass initializer, set `ALL_PARTY_SETS` to a
   tuple of dicts giving the slug and name of each party set. It
   must also override the `party_data_to_party_sets` method,
   which should take a party data dictionary (essentially the
   Python version of the party's Popolo JSON from
   `all-parties-from-popit.json`) and return a list of slugs of
   the party sets that party is in. Here are examples for the UK
   and Argentina:
   * https://github.com/mysociety/yournextrepresentative/blob/master/elections/uk_general_election_2015/lib.py#L11-L31
   * https://github.com/mysociety/yournextrepresentative/blob/master/elections/ar_elections_2015/lib.py#L87-L102
2. Create a class `AreaPostData` inheriting from
   `BaseAreaPostData` which overrides
   `post_id_to_party_set`. This method should take a post ID and
   return the slug of the party set that should be used for that
   post. Here are examples for the UK and Argentina:
   * https://github.com/mysociety/yournextrepresentative/blob/master/elections/uk_general_election_2015/lib.py#L45-L53
   * https://github.com/mysociety/yournextrepresentative/blob/master/elections/ar_elections_2015/lib.py#L120-L126

Once you've made those updates, you'll also need to generate a
Javascript file with data about the party sets by running the
Django management command
[candidates_make_party_sets_lookup](https://github.com/mysociety/yournextrepresentative/blob/master/candidates/management/commands/candidates_make_party_sets_lookup.py)
and commit the generated `post-to-party-set.js` file.

#### Post Groups

Each post can be in a particular "post group"; these are only
used to group the posts on the party detail page for a
particular election. (For example, in the UK General Election,
it was useful to group posts on that page by whether they were
associated with a constituency in England, Scotland, Northern
Ireland or Wales.)

To create multiple post groups, you must create a class
`AreaPostData`, inheriting from `BaseAreaPostData` and override
these methods:

* `__init__` - after calling the superclass initializer, set
  `self.ALL_POSSIBLE_PARTY_SETS` to a list of the names of all
  post groups. Example:
  * https://github.com/mysociety/yournextrepresentative/blob/master/elections/uk_general_election_2015/lib.py#L36-L40
* `area_to_post_group` - this should take area data (a MapIt
  area data dictionary) and return the name of the post group
  that area is associated with. Example:
  * https://github.com/mysociety/yournextrepresentative/blob/master/elections/uk_general_election_2015/lib.py#L42-L43
* `post_id_to_post_group` should take an election and a post ID
  and return the name of a post group. Example:
  * https://github.com/mysociety/yournextrepresentative/blob/master/elections/uk_general_election_2015/lib.py#L55-L60
