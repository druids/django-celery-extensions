import os

import shlex

from django.conf import settings as django_settings
from django.core.management.base import BaseCommand
from django.utils.autoreload import run_with_reloader, DJANGO_AUTORELOAD_ENV

from celery.bin.celery import celery


def autoreload_celery(celery_type, celery_settings, extra_arguments):
    celery(shlex.split(get_celery_command(
        celery_type=celery_type,
        celery_pool='solo',
        celery_settings=celery_settings,
        extra_arguments=extra_arguments
    )))


def get_celery_command(celery_type, celery_pool, celery_settings, extra_arguments=None, add_queue=True):
    celery_cmd = f'--app {celery_settings} {celery_type}'
    if extra_arguments:
        celery_cmd += f' {extra_arguments}'
    if celery_type == 'worker':
        if celery_pool:
            celery_cmd += f' --pool {celery_pool}'

        if add_queue and hasattr(django_settings, 'CELERY_LISTEN_QUEUES'):
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
            '--pool', dest='pool',
            help='Celery pool implementation.'
        )
        parser.add_argument(
            '--extra', dest='extra_args',
            help='Celery extra arguments"'
        )

    def handle(self, *args, **options):
        celery_type = options.get('type')
        celery_settings = options.get('celery_settings')
        celery_pool = options.get('pool')
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
            celery(shlex.split(get_celery_command(
                celery_type=celery_type,
                celery_pool=celery_pool,
                celery_settings=celery_settings,
                extra_arguments=extra_arguments
            )))
