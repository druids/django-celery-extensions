from settings.celery import app as celery_app
from settings.celery import CeleryQueue

from datetime import timedelta


@celery_app.task(
    bind=True,
    name='sum_task')
def sum_task(self, a, b):
    return a + b


@celery_app.task(
    bind=True,
    name='error_task',
    stale_time_limit=60 * 60)
def error_task(self):
    raise RuntimeError('error')


@celery_app.task(
    bind=True,
    name='retry_task',
    autoretry_for=(RuntimeError,),
    default_retry_delays=(1 * 60, 5 * 60, 10 * 60, 30 * 60, 60 * 60))
def retry_task(self):
    if self.request.retries != 5:
        raise RuntimeError('error')
    return self.request.retries


@celery_app.task(
    bind=True,
    name='unique_task',
    unique=True)
def unique_task(self):
    return 'unique'


@celery_app.task(
    bind=True,
    name='ignored_after_success_task',
    ignore_task_after_success_timedelta=timedelta(hours=1, minutes=5))
def ignored_after_success_task(self):
    return 'ignored_task_after_success'


@celery_app.task(
    bind=True,
    name='ignored_after_error_task',
    ignore_task_after_success_timedelta=timedelta(hours=1, minutes=5))
def ignored_after_error_task(self):
    raise RuntimeError('error')


@celery_app.task(
    queue=CeleryQueue.FAST)
def task_with_fast_queue():
    return 'result'
