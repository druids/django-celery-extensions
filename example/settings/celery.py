from django_celery_extensions.celery import Celery, CeleryQueueEnum


app = Celery('example')

# Using a string here means the worker will not have to
# pickle the object when using Windows.
app.config_from_object('django.conf:settings')
app.autodiscover_tasks()


class CeleryQueue(CeleryQueueEnum):

    FAST = ('fast', {'time_limit': 10})
