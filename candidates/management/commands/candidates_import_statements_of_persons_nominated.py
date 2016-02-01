from __future__ import print_function, unicode_literals

import csv
import errno
import hashlib
import magic
import mimetypes
import os
from os.path import dirname, join, exists
import requests

from django.core.management.base import BaseCommand, CommandError
from django.core.files.storage import FileSystemStorage 

from official_documents.models import OfficialDocument
from elections.models import Election
from popolo.models import Post, Area

CSV_URL = 'https://docs.google.com/a/mysociety.org/spreadsheets/d/1jvWaQSENnASZfGne1IWRbDATMH2NT2xutyPEbZ5Is-8/export?format=csv&id=1jvWaQSENnASZfGne1IWRbDATMH2NT2xutyPEbZ5Is-8&gid=0'

allowed_mime_types = set([
    b'application/pdf',
    b'application/msword',
    b'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
])

def download_file_cached(url):
    url_hash = hashlib.md5(url).hexdigest()
    directory = join(dirname(__file__), '.noms-cache')
    try:
        os.mkdir(directory)
    except OSError as e:
        if e.errno != errno.EEXIST:
            raise
    filename = join(directory, url_hash)
    if exists(filename):
        return filename
    r = requests.get(url, verify=False)
    with open(filename, 'w') as f:
        f.write(r.content)
    return filename

class Command(BaseCommand):
    args = "<ELECTION_SLUG>"

    def handle(self, *args, **options):

        slug, = args

        try:
            election = Election.objects.get(slug=slug)
        except Election.DoesNotExist:
            raise CommandError('No election with slug {0} found'.format(slug))

        mime_type_magic = magic.Magic(mime=True)
        storage = FileSystemStorage()

        r = requests.get(CSV_URL, stream=True)
        reader = csv.DictReader(r.raw)
        for row in reader:
            name = row['Constituency'].decode('utf-8')
            if not name:
                continue

            try:
                area = Area.objects.get(name=name)
            except Area.DoesNotExist:
                print("Failed to find area for {0}".format(name))

            try:
                post = Post.objects.get(area=area)
            except Post.DoesNotExist:
                print("Failed to find post with for {0}".format(name))

            document_url = row['Statement of Persons Nominated (SOPN) URL']
            if not document_url:
                print("No URL for {0}".format(name))
                continue
            existing_documents = OfficialDocument.objects.filter(
                post_id=post
            )
            if existing_documents.count() > 0:
                print("Skipping {0} since it already had documents".format(name))
                continue
            try:
                downloaded_filename = download_file_cached(document_url)
            except requests.exceptions.ConnectionError:
                print("Connection failed for {0}".format(name))
                print("The URL was:", document_url)
                continue
            mime_type = mime_type_magic.from_file(downloaded_filename)
            extension = mimetypes.guess_extension(mime_type)
            if mime_type not in allowed_mime_types:
                print("Ignoring unknown MIME type {0} for {1}".format(
                    mime_type,
                    name,
                ))
                continue
            filename = "official_documents/{post_id}/statement-of-persons-nominated{extension}".format(
                post_id=post.extra.slug,
                extension=extension,
            )
            with open(downloaded_filename, 'rb') as f:
                storage_filename = storage.save(filename, f)

            OfficialDocument.objects.create(
                document_type=OfficialDocument.NOMINATION_PAPER,
                uploaded_file=storage_filename,
                election=election,
                post=post,
                source_url=document_url
            )
            message = "Successfully added the Statement of Persons Nominated for {0}"
            print(message.format(name))
