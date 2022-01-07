import sys

import shlex

from django.utils.autoreload import run_with_reloader

from celery.bin.celery import celery


def autoreload_celery():
    command = shlex.split(' '.join(sys.argv[1:]))
    if 'worker' in command:
        command.append('--pool=solo')
    celery(command)


def celery_autoreload():
    run_with_reloader(autoreload_celery)


if __name__ == '__main__':
    celery_autoreload()
