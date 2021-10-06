import os

import shlex
import subprocess

from django.conf import settings as django_settings
from django.core.management.base import BaseCommand
from django.utils.autoreload import run_with_reloader, DJANGO_AUTORELOAD_ENV

import signal


def kill_celery(celery_type, celery_settings):
    kill_celery_command = f'pkill -9 -f "{get_celery_command(celery_type, celery_settings, add_queue=False)}"'
    subprocess.call(shlex.split(kill_celery_command))


def autoreload_celery(celery_type, celery_settings, extra_arguments):
    kill_celery(celery_type, celery_settings)
    subprocess.call(shlex.split(get_celery_command(celery_type, celery_settings, extra_arguments)))


def get_celery_command(celery_type, celery_settings, extra_arguments=None, add_queue=True):
    celery_cmd = f'celery --app {celery_settings} {celery_type}'
    if extra_arguments:
        celery_cmd += f' {extra_arguments}'

    if add_queue and celery_type == 'worker' and hasattr(django_settings, 'CELERY_LISTEN_QUEUES'):
        listen_queues = ' '.join(django_settings.CELERY_LISTEN_QUEUES)
        celery_cmd += f' -Q {listen_queues}'
    return celery_cmd


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
        celery_type = options.get('type')
        celery_settings = options.get('celery_settings')
        extra_arguments = options.get('extra_args', '')
        if options.get('use_reloader'):
            if os.environ.get(DJANGO_AUTORELOAD_ENV) != 'true':
                self.stdout.write('Starting celery with autoreload...')
            run_with_reloader(
                autoreload_celery,
                celery_type=celery_type,
                celery_settings=celery_settings,
                extra_arguments=extra_arguments
            )
        else:
            self.stdout.write('Starting celery...')
            process = subprocess.Popen(
                shlex.split(get_celery_command(celery_type, celery_settings, extra_arguments))
            )
            signal.signal(signal.SIGTERM, lambda *args: process.terminate())
            process.wait()
