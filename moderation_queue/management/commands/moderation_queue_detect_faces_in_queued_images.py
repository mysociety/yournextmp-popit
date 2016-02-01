from __future__ import unicode_literals

from PIL import Image

from django.core.management.base import BaseCommand

from moderation_queue.models import QueuedImage
from moderation_queue.faces import face_crop_bounds

class Command(BaseCommand):

    def handle(self, **options):

        for qi in QueuedImage.objects.filter(decision='undecided'):
            if qi.face_detection_tried:
                continue
            im = Image.open(qi.image.path)
            guessed_crop_bounds = face_crop_bounds(im)
            im.close()
            if guessed_crop_bounds:
                qi.crop_min_x, qi.crop_min_y, qi.crop_max_x, qi.crop_max_y = \
                                                                             guessed_crop_bounds
                if int(options['verbosity']) > 1:
                    self.stdout.write("Set bounds of {0} to {1}".format(
                        qi, guessed_crop_bounds
                    ))
            else:
                self.stdout.write("Couldn't find a face in {0}".format(qi))
            qi.face_detection_tried = True
            qi.save()
