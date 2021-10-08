from enum import Enum

from celery import Celery as BaseCelery


class CeleryQueueEnum(str, Enum):

    def __new__(cls, value, default_task_kwargs):
        obj = str.__new__(cls, value)
        obj._value_ = value
        obj.queue_name = value
        obj.default_task_kwargs = default_task_kwargs or {}
        return obj

    def __str__(self):
        return self.queue_name


class Celery(BaseCelery):

    task_cls = 'django_celery_extensions.task:DjangoTask'
