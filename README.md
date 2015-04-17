# A PopIt frontend for sourcing candidate data

The idea of this project is to make a web-based front-end to
[PopIt](http://popit.poplus.org/) for crowd-sourcing candidates
who are standing in the next UK general election in 2015.

This is pretty functional now - we're testing with small numbers
of users at the moment, but will make it more widely available
soon.

## Known Bugs

You can find a list of known issues to work on here:

* https://github.com/mysociety/yournextmp-popit/issues

These are prioritized in Huboard:

* https://huboard.com/mysociety/yournextmp-popit

## Getting a development version running:

Make a new directory called `yournextmp`, change into that directory and clone the repository with:

    git clone --recursive <REPOSITORY-URL>

Copy the example Vagrantfile to the root of your new directory:

    cp yournextmp-popit/Vagrantfile-example ./Vagrantfile

Copy the example configuration file to `conf/general.yml`:

    cp yournextmp-popit/conf/general.yml-example yournextmp-popit/conf/general.yml

Edit `yournextmp-popit/conf/general.yml` to fill in details of
the PopIt instance you're using.

Start that vagrant box with:

    vagrant up

Log in to the box with:

    vagrant ssh

Move to the app directory

    cd yournextmp-popit

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

    cd yournextmp-popit
    ./manage.py runserver 0.0.0.0:8000

### Running the tests

SSH into the vagrant machine, then run:

    cd yournextmp-popit
    ./manage.py test

### Mirror the live database into your development copy

Download the live database, and save the location in an
environment variable:

    ./manage.py candidates_get_live_database
    export DUMP_DIRECTORY="$(pwd)"

Assuming you have a local development instance of PopIt, change
into the root of the PopIt repository, and run:

     NODE_ENV=development bin/replace-database \
         "$DUMP_DIRECTORY"/yournextmp-popit- \
         candidates \
         popitdev__master

... replacing `candidates` with the slug of your YourNextMP
PopIt instance, and `popitdev__master` with the name of your PopIt
master database in MongoDB.

Then set the maximum PopIt person ID by running:

    ./manage.py candidates_set_max_person_id
