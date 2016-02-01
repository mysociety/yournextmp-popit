# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from datetime import date

from django.conf import settings
from django.db import models, migrations

def load_election_data(apps, schema_editor):
    Election = apps.get_model("elections", "Election")
    AreaType = apps.get_model("elections", "AreaType")
    db_alias = schema_editor.connection.alias
    if settings.ELECTION_APP == 'uk_general_election_2015':
        area, created = AreaType.objects.using(db_alias).get_or_create(
            name='WMC'
        )

        Election.objects.using(db_alias).bulk_create([
            Election(
                candidate_membership_role="Candidate",
                use_for_candidate_suggestions=False,
                name="2015 General Election",
                election_date=date(2015, 5, 7),
                organization_name="House of Commons",
                area_generation="22",
                winner_membership_role="",
                current=True,
                party_membership_end_date=date(9999, 12, 31),
                post_id_format="{area_id}",
                candidacy_start_date=date(2010, 5, 7),
                party_membership_start_date=date(2010, 5, 7),
                organization_id="commons",
                slug="2015",
                for_post_role="Member of Parliament",
                description="2015 General Election",
                show_official_documents=True
            ),
            Election(
                candidate_membership_role="Candidate",
                use_for_candidate_suggestions=True,
                name="2010 General Election",
                election_date=date(2010, 5, 6),
                organization_name="House of Commons",
                area_generation="22",
                winner_membership_role="",
                for_post_role="Member of Parliament",
                current=False,
                party_membership_end_date=date(2010, 5, 6),
                post_id_format="{area_id}",
                candidacy_start_date=date(2005, 5, 6),
                party_membership_start_date=date(2005, 5, 6),
                organization_id="commons",
                slug="2010",
                description="2010 General Election",
                show_official_documents=True
            )
        ])
        for election in Election.objects.using(db_alias).all():
            election.area_types.add(area)

    elif settings.ELECTION_APP == 'ar_elections_2015':
        prv, created = AreaType.objects.using(db_alias).get_or_create(
            name='PRV'
        )
        nat, created = AreaType.objects.using(db_alias).get_or_create(
            name='NAT'
        )

        Election.objects.using(db_alias).bulk_create([
            Election(
                slug="diputados-argentina-paso-2015",
                for_post_role="Diputado Nacional",
                candidate_membership_role="Primary Candidate",
                winner_membership_role="Candidate",
                election_date=date(2015, 8, 9),
                candidacy_start_date=date(2015, 6, 22),
                name="Diputados Nacionales PASO 2015",
                current=True,
                use_for_candidate_suggestions=False,
                party_membership_start_date=date(2015, 6, 22),
                party_membership_end_date=date(9999, 12, 31),
                area_generation="1",
                organization_id="hcdn",
                organization_name="Cámara de Diputados",
                post_id_format="dip-{area_id}",
            ),
            Election(
                slug="gobernadores-argentina-paso-2015",
                for_post_role="Gobernador",
                candidate_membership_role="Primary Candidate",
                winner_membership_role="Candidate",
                election_date=date(2015, 8, 9),
                candidacy_start_date=date(2015, 6, 22),
                name="Gobernador PASO 2015",
                current=True,
                party_membership_start_date=date(2015, 6, 22),
                party_membership_end_date=date(9999, 12, 31),
                area_generation="1",
                organization_id="gobernador",
                organization_name="Gobernador",
                post_id_format="gob-{area_id}",
            ),
            Election(
                slug="senadores-argentina-paso-2015",
                for_post_role="Senador Nacional",
                candidate_membership_role="Primary Candidate",
                winner_membership_role="Candidate",
                election_date=date(2015, 8, 9),
                candidacy_start_date=date(2015, 6, 22),
                name="Senadores Nacionales PASO 2015",
                current=True,
                party_membership_start_date=date(2015, 6, 22),
                party_membership_end_date=date(9999, 12, 31),
                area_generation="1",
                organization_id="hcsn",
                organization_name="Senado de la Nación",
                post_id_format="sen-{area_id}",
            ),
            Election(
                slug="presidentes-argentina-paso-2015",
                for_post_role="Presidente",
                candidate_membership_role="Primary Candidate",
                winner_membership_role="Candidate",
                election_date=date(2015, 8, 9),
                candidacy_start_date=date(2015, 6, 22),
                organization_id="pen",
                organization_name="Presidencia de la Nación Argentina",
                name="Presidentes PASO 2015",
                current=True,
                party_membership_start_date=date(2015, 6, 22),
                party_membership_end_date=date(9999, 12, 31),
                area_generation="1",
                post_id_format="presidente",
            ),
            Election(
                slug='parlamentarios-mercosur-regional-paso-2015',
                for_post_role='Parlamentario Mercosur',
                candidate_membership_role='Primary Candidate',
                winner_membership_role='Candidate',
                election_date=date(2015, 8, 9),
                candidacy_start_date=date(2015, 6, 22),
                name='Parlamentario Mercosur PASO 2015',
                current=True,
                party_membership_start_date=date(2015, 6, 22),
                party_membership_end_date=date(9999, 12, 31),
                area_generation=1,
                organization_id='parlmercosur',
                organization_name='Parlamento del Mercosur',
                post_id_format='pmer-{area_id}',
                party_lists_in_use=True,
                default_party_list_members_to_show=3,
            ),
            Election(
                slug='parlamentarios-mercosur-unico-paso-2015',
                for_post_role='Parlamentario Mercosur',
                candidate_membership_role='Primary Candidate',
                winner_membership_role='Candidate',
                election_date=date(2015, 8, 9),
                candidacy_start_date=date(2015, 6, 22),
                name='Parlamentario Mercosur PASO 2015',
                current=True,
                party_membership_start_date=date(2015, 6, 22),
                party_membership_end_date=date(9999, 12, 31),
                area_generation=1,
                organization_id='parlmercosur',
                organization_name='Parlamento del Mercosur',
                post_id_format='pmeu',
                party_lists_in_use=True,
                default_party_list_members_to_show=3,
            ),
        ])

        for election in Election.objects.using(db_alias).all():
            if election.slug == 'presidentes-argentina-paso-2015' \
               or election.slug == 'parlamentarios-mercosur-unico-paso-2015':
                election.area_types.add(nat)
            else:
                election.area_types.add(prv)

    elif settings.ELECTION_APP == 'bf_elections_2015':
        national, created = AreaType.objects.using(db_alias).get_or_create(
            name='NATIONAL'
        )
        province, created = AreaType.objects.using(db_alias).get_or_create(
            name='PROVINCE'
        )

        Election.objects.using(db_alias).bulk_create([
            Election(
                slug='pres-2015',
                current=True,
                for_post_role='Président du Faso',
                candidate_membership_role='Candidat',
                election_date=date(2015, 10, 11),
                candidacy_start_date=date(2010, 11, 22),
                organization_id='presidence',
                organization_name='Présidence',
                party_membership_start_date=date(2010, 11, 22),
                party_membership_end_date=date(9999, 12, 31),
                party_lists_in_use=False,
                name='Elections Présidentielles de 2015',
                area_generation=2,
                post_id_format='president',
                show_official_documents=False,
            ),
            Election(
                slug='nat-2015',
                current=True,
                for_post_role='Député National',
                candidate_membership_role='Candidat',
                election_date=date(2015, 10, 11),
                candidacy_start_date=date(2012, 12, 3),
                organization_id='assemblee-nationale',
                organization_name='Assemblée nationale',
                party_membership_start_date=date(2012, 12, 3),
                party_membership_end_date=date(9999, 12, 31),
                party_lists_in_use=True,
                default_party_list_members_to_show=2,
                name='Elections Législative de 2015',
                area_generation=2,
                post_id_format='nat-{area_id}',
                show_official_documents=False,
            ),
            Election(
                slug='prv-2015',
                current=True,
                for_post_role='Député Provincial',
                candidate_membership_role='Candidat',
                election_date=date(2015, 10, 11),
                candidacy_start_date=date(2012, 12, 3),
                organization_id='assemblee-nationale',
                organization_name='Assemblée nationale',
                party_membership_start_date=date(2012, 12, 3),
                party_membership_end_date=date(9999, 12, 31),
                party_lists_in_use=True,
                default_party_list_members_to_show=2,
                name='Elections Législative de 2015',
                area_generation=2,
                post_id_format='prv-{area_id}',
                show_official_documents=False,
            )
        ])

        for election in Election.objects.using(db_alias).all():
            if election.slug == 'prv-2015':
                election.area_types.add(province)
            else:
                election.area_types.add(national)

    elif settings.ELECTION_APP == 'st_paul_municipal_2015':
        muni, created = AreaType.objects.using(db_alias).get_or_create(
            name='MUNI'
        )
        ward, created = AreaType.objects.using(db_alias).get_or_create(
            name='WARD'
        )

        Election.objects.using(db_alias).bulk_create([
            Election(
                slug='council-member-2015',
                for_post_role='Council Member',
                candidate_membership_role='Candidate',
                winner_membership_role='Candidate',
                election_date=date(2015, 11, 3),
                candidacy_start_date=date(2015, 6, 22),
                name='City Council Election',
                current=True,
                use_for_candidate_suggestions=False,
                party_membership_start_date=date(2015, 6, 22),
                party_membership_end_date=date(9999, 12, 31),
                party_lists_in_use=False,
                organization_id='saint-paul-city-council',
                organization_name='Saint Paul City Council',
                post_id_format='ocd-division,country:us,state:mn,place:st_paul,ward:{area_id}',
                ocd_division='ocd-division/country:us/state:mn/place:st_paul/ward',
                area_generation=1,
            ),
            Election(
                slug='school-board-2015',
                for_post_role='School Board Member',
                candidate_membership_role='Candidate',
                winner_membership_role='Candidate',
                election_date=date(2015, 11, 3),
                candidacy_start_date=date(2015, 6, 22),
                name='School Board Election',
                current=True,
                use_for_candidate_suggestions=False,
                party_membership_start_date=date(2015, 6, 22),
                party_membership_end_date=date(9999, 12, 31),
                party_lists_in_use=False,
                area_generation=1,
                organization_id='saint-paul-school-board',
                organization_name='Saint Paul School Board',
                post_id_format='ocd-division,country:us,state:mn,place:st_paul',
                ocd_division='ocd-division/country:us/state:mn/place:st_paul',
            )
        ])

        for election in Election.objects.using(db_alias).all():
            if election.slug == 'council-member-2015':
                election.area_types.add(ward)
            else:
                election.area_types.add(muni)


class Migration(migrations.Migration):

    dependencies = [
        ('elections', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(load_election_data),
    ]
