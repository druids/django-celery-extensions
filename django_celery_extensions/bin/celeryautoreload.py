import os
import sys

import shlex

from django.utils.autoreload import run_with_reloader

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

        if add_queue:
            listen_queues = 'fast.fifo'
            celery_cmd += f' -Q {listen_queues}'
    return celery_cmd


def celery_autoreload():
    run_with_reloader(
        autoreload_celery,
        celery_type='worker',
        celery_settings='common.celery',
        extra_arguments='-Ofair --concurrency 2 --loglevel INFO'
    )


if __name__ == '__main__':
    celery_autoreload()
