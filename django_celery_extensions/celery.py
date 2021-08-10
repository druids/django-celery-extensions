from enum import Enum

from celery import Celery as BaseCelery


class CeleryQueueEnum(Enum):

    def __init__(self, queue_name, default_task_kwargs=None):
        self.queue_name = queue_name
        self.default_task_kwargs = default_task_kwargs or {}

    def __str__(self):
        return self.queue_name


class Celery(BaseCelery):

    task_cls = 'django_celery_extensions.task:DjangoTask'

    def task(self, *args, **kwargs):
        queue = kwargs.pop('queue', None)
        if isinstance(queue, CeleryQueueEnum):
            kwargs['queue'] = queue.queue_name
            kwargs = {
                **queue.default_task_kwargs,
                **kwargs,
            }
        return super().task(*args, **kwargs)
