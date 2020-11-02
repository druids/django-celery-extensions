.. _config:

=============
Configuration
=============

You can configure the library in Django settings. Following options are available:

* ``DJANGO_CELERY_EXTENSIONS_CACHE_NAME`` (default: ``'default'``)

    Name of the django cache used for locked scheduler and uniqueness of a task.


* ``DJANGO_CELERY_EXTENSIONS_KEY_PREFIX`` (default: ``'django-celery-extensions'``)

    Cache key prefix used for locked scheduler and uniqueness of a task.


* ``DJANGO_CELERY_EXTENSIONS_LOCK_KEY`` (default: ``'lock'``)

    Name of the key used for locked scheduler.


* ``DJANGO_CELERY_EXTENSIONS_LOCK_TIMEOUT`` (default: ``celery.beat.DEFAULT_MAX_INTERVAL * 5``)

    Time of the scheduler lock.


* ``DJANGO_CELERY_EXTENSIONS_LOCK_SLEEP`` (default: ``celery.beat.DEFAULT_MAX_INTERVAL``)

    Sleep time interval to check if schduler is still locked.


* ``DJANGO_CELERY_EXTENSIONS_DEFAULT_TASK_STALE_TIME_LIMIT`` (default: ``None``)

    Default time of the task when it will be set as stale.


* ``DJANGO_CELERY_EXTENSIONS_DEFAULT_TASK_MAX_QUEUE_WAITING_TIME`` (default: ``None``)

    Maximal time which task will be waiting in the queue. Value of ``task_stale_limit`` can be computed from this value.


* ``DJANGO_CELERY_EXTENSIONS_AUTO_GENERATE_TASKS_DJANGO_COMMANDS`` (default: ``{}``)

    Dictionary of django commands which will be converted into celery tasks.


* ``DJANGO_CELERY_EXTENSIONS_AUTO_GENERATE_TASKS_DEFAULT_CELERY_KWARGS`` (default: ``{}``)

    Default celery task kwargs which will be used for auto generated tasks from django commands.
