=====
Usage
=====

Tasks
-----

Library adds two implementation of celery task class and improve it with several functions:


DjangoTask
^^^^^^^^^^

Class which extends ``celery.Task`` and adds functions that simplify celery usage with ``Django`` framework.

Let's create task with this base::

    from django.contrib.auth.models import User
    from django_celery_extensions.task import DjangoTask

    @celery_app.task(
        base=DjangoTask,
        bind=True)
    def notify_user(self, user_pk):
        user = User.objects.get(pk=user_pk)
        was_notified = notify(user)
        return was_notified


Because ``Django`` framework often uses atomic transactions it is recomended call celery tasks via ``on_commit`` function. ``DjangoTask`` simplifies it with several methods::

    notify_user.apply_async_on_commit(args=(user.pk,))  # similar to apply_async but with on_commit
    notify_user.delay_on_commit(user.pk)  # similar to delay but with on_commit
    notify_user.apply_async_and_get_result(args=(user.pk,), timeout=None, propagate=True)  # call apply_async and wait specified timeout to task result. If result is not obtained to the specified time ``TimeoutError`` is raised

If you want to use celery autoretry but you want different retry times for different attempts, you can use default_retry_delays::

    @celery_app.task(
        base=DjangoTask,
        bind=True,
        autoretry_for=(NotifyException,),
        default_retry_delays(60, 120, 180))
    def notify_user(self, user_pk):
        user = User.objects.get(pk=user_pk)
        was_notified = notify(user)
        return was_notified

The task will be retried three times. First attempt will be after 60 second, the second attempt will be after 120 second and third after 180 second.

Sometimes it is necessary for a task with the same input to run only once. For this purpose you can use unique configuration::


    @celery_app.task(
        base=DjangoTask,
        bind=True,
        unique=True,
        stale_time_limit=60)
    def notify_user(self, user_pk):
        user = User.objects.get(pk=user_pk)
        was_notified = notify(user)
        return was_notified

Task will be now run only once if you fill apply it two times at the same time. Attribute ``stale_time_limit`` defines maximum nuber of seconds how long the task lock will be applied.


Sometimes it is good convert ``Django`` commands to celery task. For example when you want to use celery beater instead of cron. For this purpose you can use ``DJANGO_CELERY_EXTENSIONS_AUTO_GENERATE_TASKS_DJANGO_COMMANDS`` setting to define which commands you want to convert into tasks::

    DJANGO_CELERY_EXTENSIONS_AUTO_GENERATE_TASKS_DJANGO_COMMANDS = {
        'clearsessions': {'unique': True},
    }

Commands are defined in dictionary where key is name of the command and value is dictionary of celery task configuration. Celery base task class is ``DjangoTask`` therefore supports all its functions.

If you want to call the command tasky by hand, you can use ``get_django_command_task`` to get the task::

    from django_celery_extensions.task import get_django_command_task

    get_django_command_task('clearsessions').delay_on_commit()


Some tasks can be run only once per specific time. For this purpose you can use ``ignore_task_after_success_timedelta``::

    @celery_app.task(
        base=DjangoTask,
        bind=True,
        ignore_task_after_success_timedelta=timedelta(hours=5))
    def notify_user(self, user_pk):
        user = User.objects.get(pk=user_pk)
        was_notified = notify(user)
        return was_notified

Now ``notify_user`` task will be ignored for 5 hours after the last successful completion::

    notify_user.delay(5).state  # result will be SUCCESS
    notify_user.delay(5).state  # result will be IGNORED
    # wait 5 hours
    notify_user.delay(5).state  # result will be SUCCESS

If task ends in failure state it can be run again and will not be ignored. 


Beater
------

Celery documentation warns against running more than one beater. But sometimes is necessary have more instances (for example in the cloud deployments). You can use ``django_celery_extensions.beat.LockedPersistentScheduler`` to ensure that only one instance of beater will be active. Only run celery beater with this scheduler to ensure it::

    celery -A proj beat -s django_celery_extensions.beat.LockedPersistentScheduler

The scheduler will only work with configured ``redis_cache.RedisCache`` in ``Django`` settings.

Commands
--------

For development purposes ``Django`` provides autoreload funkcionality, which restarts django application when code is changes. Celery unfortunately doesn't support it but you can run celery via django command to achieve it::

    ./manage.py run_celery --type=worker/beater --celerysettings=settings.celery --autoreload --extra="some extra celery arguments"
