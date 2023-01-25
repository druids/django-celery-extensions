.. _config:

=============
Configuration
=============

You can configure the library in Django settings. Following options are available:

* ``DJANGO_CELERY_EXTENSIONS_CACHE_NAME`` (default: ``'default'``)

    Name of the django cache used for locked scheduler and uniqueness of a task.


* ``DJANGO_CELERY_EXTENSIONS_BEATER_LOCK_KEY`` (default: ``'django-celery-extensions|lock''``)

    Cache key prefix used for locked scheduler.

* ``DJANGO_CELERY_EXTENSIONS_IUNIQUE_TASK_KEY_PREFIX`` (default: ``'django-celery-extensions|unique''``)

    Value of the setting is used to generate cache key for the uniqueness of the tasks.

* ``DJANGO_CELERY_EXTENSIONS_IGNORE_TASK_KEY_PREFIX`` (default: ``'django-celery-extensions|ignore''``)

    Value of the setting is used to generate cache key for the tasks ignore logic.

* ``DJANGO_CELERY_EXTENSIONS_LOCK_TIMEOUT`` (default: ``celery.beat.DEFAULT_MAX_INTERVAL * 5``)

    Time of the scheduler lock.

* ``DJANGO_CELERY_EXTENSIONS_LOCK_SLEEP`` (default: ``celery.beat.DEFAULT_MAX_INTERVAL``)

    Sleep time interval to check if schduler is still locked.

* ``DJANGO_CELERY_EXTENSIONS_DEFAULT_TASK_STALE_TIME_LIMIT`` (default: ``None``)

    Default time of the task when it will be set as stale.

* ``DJANGO_CELERY_EXTENSIONS_DEFAULT_TASK_MAX_QUEUE_WAITING_TIME`` (default: ``None``)

    Maximal time which task will be waiting in the queue. Value of ``task_stale_limit`` can be computed from this value.

* ``DJANGO_CELERY_EXTENSIONS_AUTO_GENERATE_TASKS_DJANGO_COMMANDS`` (default: ``{}``)

    Dictionary of django commands which will be converted into celery tasks::

    DJANGO_CELERY_EXTENSIONS_AUTO_GENERATE_TASKS_DJANGO_COMMANDS = {
        'django_command_name': {
            'queue': 'fast',
            # Another celery task configuration
        }


    }

* ``DJANGO_CELERY_EXTENSIONS_CELERY_AUTODISCOVER`` (default: ``False``)

    Run the celery tasks auto discover after the Django application initialization.

* ``DJANGO_CELERY_EXTENSIONS_CELERY_SETTINGS`` (default: ``None``)

    Path to the celery setting which is automatically imported after the Django application initialization.

* ``DJANGO_CELERY_EXTENSIONS_CELERY_TASK_CHECKER`` (default: ``None``)

    Path to the module with implemented Django checker of the celery tasks configuration::

    # Django settings
    DJANGO_CELERY_EXTENSIONS_CELERY_TASK_CHECKER = 'celery_check'

    # celery_check.py file
    from django.core.checks import Error

    def check_celery_task(task_name, task):
        if not hasattr(task, 'queue'):
            return Error(
                f'Task with name "{task_name}" has not set queue',
                hint=f'Set one of celery task queues "{CeleryQueue}"',
                id='celery_task.E001',
                obj=task
            )

* ``DJANGO_CELERY_EXTENSIONS_AUTO_GENERATE_TASKS_DEFAULT_CELERY_KWARGS`` (default: ``{}``)

    Default celery task kwargs which will be used for auto generated tasks from django commands::

    DJANGO_CELERY_EXTENSIONS_AUTO_GENERATE_TASKS_DEFAULT_CELERY_KWARGS = {'queue': 'fast'}  # All celery tasks will be set with the fast celery queue


* ``DJANGO_CELERY_EXTENSIONS_AUTO_SQS_MESSAGE_GROUP_ID`` (default: ``False``)

    Whether to automatically set `MessageGroupId <https://docs.aws.amazon.com/AWSSimpleQueueService/latest/SQSDeveloperGuide/using-messagegroupid-property.html>` to Celery task name or not. Is recommended use this settings with the AWS SQS queue.
