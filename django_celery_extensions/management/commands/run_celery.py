import shlex
import subprocess

from django.conf import settings as django_settings
from django.core.management.base import BaseCommand
from django.utils.autoreload import run_with_reloader


def start_celery(celery_type, celery_settings, extra_arguments, autoreload=False):
    starter_celery_cmd = 'celery {} -l info -A {} {}'.format(celery_type, celery_settings, extra_arguments)
    if celery_type == 'worker' and hasattr(django_settings, 'CELERY_LISTEN_QUEUES'):
        starter_celery_cmd += ' -Q {}'.format(django_settings.CELERY_LISTEN_QUEUES)

    if autoreload:
        kill_worker_cmd = 'pkill -9 -f "{}"'.format(starter_celery_cmd)
        subprocess.call(shlex.split(kill_worker_cmd))
    subprocess.call(shlex.split(starter_celery_cmd))


class Command(BaseCommand):

    def add_arguments(self, parser):
        parser.add_argument(
            'type', help='Celery type "beat" or "worker', choices={'beat', 'worker'}
        )
        parser.add_argument(
            '--celerysettings', dest='celery_settings', type=str,
            help='Tells Django to use celery settings', required=True
        )
        parser.add_argument(
            '--autoreload', action='store_true', dest='use_reloader',
            help='Tells Django to use the auto-reloader',
        )
        parser.add_argument(
            '--extra', dest='extra_args',
            help='Celery extra arguments"'
        )

    def handle(self, *args, **options):
        if options.get('use_reloader'):
            self.stdout.write('Starting celery with autoreload...')
            run_with_reloader(
                start_celery,
                celery_type=options.get('type'),
                celery_settings=options.get('celery_settings'),
                extra_arguments=options.get('extra_args', ''),
                autoreload=True
            )
        else:
            self.stdout.write('Starting celery...')
            start_celery(
                celery_type=options.get('type'),
                celery_settings=options.get('celery_settings'),
                extra_arguments=options.get('extra_args', '')
            )
