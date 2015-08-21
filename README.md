# A PopIt frontend for sourcing candidate data

The idea of this project is to make a web-based front-end to
[PopIt](http://popit.poplus.org/) for crowd-sourcing candidates
for upcoming elections; it was used for
[YourNextMP](https://yournextmp.com) in the UK for the 2015
General Election.

## Known Bugs

You can find a list of known issues to work on here:

* https://github.com/mysociety/yournextrepresentative/issues

These are prioritized in Waffle:

* https://waffle.io/mysociety/yournextrepresentative

## Getting a development version running:

First make sure you have a running virtualbox environment. This requires having the current kernel's header package, and the hardware virtualization turned on at the BIOS level.

    sudo apt-get install virtualbox

Then install vagrant, preferably from the .deb package from the official website. 

   Follow the install instructions here: https://docs.vagrantup.com/v2/installation/

Make a new directory called `yournextmp`, change into that directory and clone the repository with:

    git clone --recursive <REPOSITORY-URL>

Copy the example Vagrantfile to the root of your new directory:

    cp yournextrepresentative/Vagrantfile-example ./Vagrantfile

Copy the example configuration file to `conf/general.yml`:

    cp yournextrepresentative/conf/general.yml-example yournextrepresentative/conf/general.yml

Edit `yournextrepresentative/conf/general.yml` to fill in details of
the PopIt instance you're using.

Start that vagrant box with:

    vagrant up

It may take several minutes to run all of the scripts for the first time. If you run into problems at this stage, you can debug your virtual machine interactively by uncommmenting the #v.ui = true in the Vagrantfile.

Log in to the box with:

    vagrant ssh

Move to the app directory

    cd yournextrepresentative

Add a superuser account:

    ./manage.py createsuperuser

Run the development server:

    ./manage.py runserver 0.0.0.0:8000

Now you should be able to see the site at:

    http://127.0.0.1.xip.io:8000/

Go to the admin interface:

    http://127.0.0.1.xip.io:8000/admin/

... and login with the superuser account.

If you want to create a PopIt database based on an existing live
instance, see the "Mirror the live database into your
development copy" section below, and follow those steps at this
stage.

### Restarting the development server after logging out

After logging in again, the only steps you should need to run
the development server again are:

    cd yournextrepresentative
    ./manage.py runserver 0.0.0.0:8000

### Running the tests

SSH into the vagrant machine, then run:

    cd yournextrepresentative
    ./manage.py test

### Mirror the live database into your development copy

Download the live database, and save the location in an
environment variable:

    ./manage.py candidates_get_live_database
    export DUMP_DIRECTORY="$(pwd)"

Assuming you have a local development instance of PopIt, change
into the root of the PopIt repository, and run:

     NODE_ENV=development bin/replace-database \
         "$DUMP_DIRECTORY"/yournextrepresentative- \
         candidates \
         popitdev__master

... replacing `candidates` with the slug of your YourNextMP
PopIt instance, and `popitdev__master` with the name of your PopIt
master database in MongoDB.

Then set the maximum PopIt person ID by running:

    ./manage.py candidates_set_max_person_id

### Customizing YourNextMP for a new election

(This is a rough description at the moment; making YourNextMP fully
generic is a work-in-progress.)

To use this code to collect informations about candidates in a new
jurisdiction, you should start by adding a new election application
under `elections` - you can use `uk_general_election_2015` as an
example. You should then set `ELECTION_APP` in your `general.yml` to
the name of that application (not including `elections.`).

In that application, you should create a `settings` module which
defines `ELECTIONS`.

If you want to customize behaviour of YourNextMP for this
jurisdiction, then you can do one of the following:

* Override generic templates in your election application.

* Add a urls.py and views.py and override and augment and of the
  generic URLs that you want to customize.

* Some data and behaviour will need to be customized by adding
  functions or variables in `lib.py` in your election application.

You will also have to decide if you you want to create "party sets" or
"post groups" for the elections you're supporting.  These are
potentially confusing, so here are some quick descriptions:

#### Party Sets

It's sometimes the case that there are different sets of parties
available for different posts that are up for election.  (For example,
in the UK General Election, there are distinct registers of parties
for constituencies in Northern Ireland and Great Britain.)

#### Post Groups

Each post can be in a particular "post group"; these are only used to
group the posts on the party detail page for a particular
election. (For example, in the UK General Election, it was useful to
group posts on that page by whether they were associated with a
constituency in England, Scotland, Northern Ireland or Wales.

FIXME: add details of translating the interface
