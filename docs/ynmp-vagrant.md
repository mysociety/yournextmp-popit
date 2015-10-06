# Notes on getting YourNextReprsentative running in a Vagrant box

**WARNING** These instructions are probably out of date - they
were created to help developers and designers get started on
working on the original UK version of this site. They may be of
some use still, however.

## Getting a development version running:

yoMake a new directory called `yournextrepresentative`, change
into that directory and clone the repository with:

    git clone --recursive <REPOSITORY-URL>

Copy the example Vagrantfile to the root of your new directory:

    cp yournextrepresentative/Vagrantfile-example ./Vagrantfile

Copy the example configuration file to `conf/general.yml`:

    cp yournextrepresentative/conf/general.yml-example yournextrepresentative/conf/general.yml

Edit `yournextrepresentative/conf/general.yml` to fill in details of
the PopIt instance you're using.

Start that vagrant box with:

    vagrant up

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

### DEPRECATED: Mirror the live database into your development copy

**IMPORTANT WARNING** This procedure works to some extent, but
essentially corrupts the data in your local PopIt database. It's
*not* the same as running mongoexport on the live site and then
importing that database dump, which is the safe way of getting a
copy of the live instance.  (If you're interested in the gory
details, some of the data included in the output of PopIt's API,
as used by the `candidates_get_live_database` command, is
generated rather than being straight from MongoDB. If you then
use the replace-database script (which uses mongoimport) as
suggested below then this generated data will be written to
MongoDB.  This has produced surprising and confusing bugs.)

Download the live database, and save the location in an
environment variable:

    ./manage.py candidates_get_live_database
    export DUMP_DIRECTORY="$(pwd)"

*(Not recommended - see the warning above.)*  Assuming you have a
local development instance of PopIt, change into the root of the
PopIt repository, and run:

     NODE_ENV=development bin/replace-database \
         "$DUMP_DIRECTORY"/yournextrepresentative- \
         candidates \
         popitdev__master

... replacing `candidates` with the slug of your YourNextMP
PopIt instance, and `popitdev__master` with the name of your PopIt
master database in MongoDB.

Then set the maximum PopIt person ID by running:

    ./manage.py candidates_set_max_person_id
