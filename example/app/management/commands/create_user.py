from django.contrib.auth.models import User
from django.core.management.base import BaseCommand


class Command(BaseCommand):

    def handle(self, **options):
        User.objects._create_user('test', 'test@test.cz', 'test', is_staff=True, is_superuser=True)
