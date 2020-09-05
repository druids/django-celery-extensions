import os
import base64
import logging
import pickle
import math

import uuid

import import_string

from datetime import timedelta

from distutils.version import StrictVersion

from django.core.management import call_command, get_commands
from django.core.exceptions import ImproperlyConfigured
from django.core.cache import caches
from django.db import close_old_connections, transaction
from django.db.utils import InterfaceError, OperationalError
from django.utils.timezone import now

try:
    from celery import VERSION as CELERY_VERSION
    from celery import Task, shared_task, current_app
    from celery.result import AsyncResult
    from celery.exceptions import CeleryError, TimeoutError
    from kombu.utils import uuid as task_uuid
except ImportError:
    raise ImproperlyConfigured('Missing celery library, please install it')

from .config import settings


logger = logging.getLogger(__name__)

CELERY_VERSION = StrictVersion('.'.join((str(i) for i in CELERY_VERSION if i)))


cache = caches[settings.CACHE_NAME]


def default_unique_key_generator(task, task_args, task_kwargs):
    def serialize_value(v):
        if isinstance(v, (tuple, list)):
            return str(list(v))
        else:
            return str(v)

    unique_key = [settings.KEY_PREFIX, task.name]
    if task_args:
        unique_key += [serialize_value(v) for v in task_args]
    if task_kwargs:
        unique_key += ['{}={}'.format(k, serialize_value(v)) for k, v in task_kwargs.items()]
    return ':'.join(unique_key)


class DjangoTask(Task):

    abstract = True

    stale_time_limit = None
    # Support set retry delay in list. Retry countdown value is get from list where index is attempt
    # number (request.retries)
    default_retry_delays = None
    # Unique task if task with same input already exists no extra task is created and old task result is returned
    unique = False
    unique_key_generator = default_unique_key_generator
    _stackprotected = True

    def on_start(self, args, kwargs):
        """
        On start task is invoked during task started.
        :param args: task args
        :param kwargs: task kwargs
        """
        pass

    def __call__(self, *args, **kwargs):
        """
        Overrides parent which works with thread stack. We didn't want to allow change context which was generated in
        one of apply methods. Call task directly is now disallowed.
        """
        req = self.request_stack.top

        if not req or req.called_directly:
            raise CeleryError(
                'Task cannot be called directly. Please use apply, apply_async or apply_async_on_commit methods'
            )

        if req._protected:
            raise CeleryError('Request is protected')
        # request is protected (no usage in celery but get from function _install_stack_protection in
        # celery library)
        req._protected = 1

        # Every set attr is sent here
        self.on_start(args, kwargs)
        return self._start(*args, **kwargs)

    def _start(self, *args, **kwargs):
        return self.run(*args, **kwargs)

    def _get_unique_key(self, task_args, task_kwargs):
        return (
            str(uuid.uuid5(uuid.NAMESPACE_DNS, self.unique_key_generator(task_args, task_kwargs)))
            if self.unique else None
        )

    def _clear_unique_key(self, task_args, task_kwargs):
        unique_key = self._get_unique_key(task_args, task_kwargs)
        if unique_key:
            cache.delete(unique_key)

    def _get_unique_task_id(self, task_id, task_args, task_kwargs, stale_time_limit):
        unique_key = self._get_unique_key(task_args, task_kwargs)

        if unique_key and not stale_time_limit:
            raise CeleryError('For unique tasks is require set task stale_time_limit')

        if unique_key and not self._get_app().conf.task_always_eager:
            if cache.add(unique_key, task_id, stale_time_limit):
                return task_id
            else:
                unique_task_id = cache.get(unique_key)
                return (
                    unique_task_id if unique_task_id
                    else self._get_unique_task_id(task_id, task_args, task_kwargs, stale_time_limit)
                )
        else:
            return task_id

    def on_failure(self, exc, task_id, args, kwargs, einfo):
        super().on_failure(exc, task_id, args, kwargs, einfo)
        self._clear_unique_key(args, kwargs)

    def on_success(self, retval, task_id, args, kwargs):
        super().on_success(retval, task_id, args, kwargs)
        self._clear_unique_key(args, kwargs)

    def _compute_eta(self, eta, countdown, apply_time):
        if countdown is not None:
            return apply_time + timedelta(seconds=countdown)
        elif eta:
            return eta
        else:
            return apply_time

    def _compute_expires(self, expires, time_limit, stale_time_limit, apply_time):
        expires = self.expires if expires is None else expires
        if expires is not None:
            return apply_time + timedelta(seconds=expires) if isinstance(expires, int) else expires
        elif stale_time_limit is not None and time_limit is not None:
            return apply_time + timedelta(seconds=stale_time_limit - time_limit)
        else:
            return None

    def _get_time_limit(self, time_limit):
        if time_limit is not None:
            return time_limit
        elif self.soft_time_limit is not None:
            return self.soft_time_limit
        else:
            return self._get_app().conf.task_time_limit

    def _get_stale_time_limit(self, expires, time_limit, stale_time_limit, apply_time):
        if stale_time_limit is not None:
            return stale_time_limit
        elif self.stale_time_limit is not None:
            return self.stale_time_limit
        elif settings.TASK_STALE_TIME_LIMIT is not None:
            return settings.TASK_STALE_TIME_LIMIT
        elif time_limit is not None and settings.TASK_STALE_TIMELIMIT_FROM_TIME_LIMIT_CONSTANT:
            return math.ceil(time_limit * settings.TASK_STALE_TIMELIMIT_FROM_TIME_LIMIT_CONSTANT)
        else:
            return None

    def on_apply(self, task_id, apply_time, stale_time_limit, args, kwargs, options):
        """
        On apply task is invoked before task was prepared. Therefore task request context is not prepared.
        :param task_id: uuid of the task
        :param apply_time: datetime instance when task was applied
        :param stale_time_limit: time limit in seconds to complete task
        :param args: task args
        :param kwargs: task kwargs
        :param options: input task options
        """
        pass

    def _first_apply(self, is_async, args=None, kwargs=None, task_id=None, eta=None,
                     countdown=None, expires=None, time_limit=None, stale_time_limit=None, **options):
        task_id = task_id or task_uuid()
        apply_time = now()
        time_limit = self._get_time_limit(time_limit)

        eta = self._compute_eta(eta, countdown, apply_time)
        countdown = None
        queue = str(options.get('queue', getattr(self, 'queue', self._get_app().conf.task_default_queue)))
        stale_time_limit = self._get_stale_time_limit(expires, time_limit, stale_time_limit, apply_time)
        expires = self._compute_expires(expires, time_limit, stale_time_limit, apply_time)

        options.update(dict(
            time_limit=time_limit,
            eta=eta,
            countdown=countdown,
            queue=queue,
            expires=expires,
        ))
        unique_task_id = self._get_unique_task_id(task_id, args, kwargs, stale_time_limit)

        if is_async and unique_task_id != task_id:
            return AsyncResult(unique_task_id, app=self._get_app())

        self.on_apply(task_id, apply_time, stale_time_limit, args, kwargs, options)
        if is_async:
            return super().apply_async(task_id=task_id, args=args, kwargs=kwargs, **options)
        else:
            return super().apply(task_id=task_id, args=args, kwargs=kwargs, **options)

    def apply_async_on_commit(self, args=None, kwargs=None, **options):
        app = self._get_app()
        if app.conf.task_always_eager:
            self.apply_async(args=args, kwargs=kwargs, **options)
        else:
            self_inst = self
            transaction.on_commit(
                lambda: self_inst.apply_async(args=args, kwargs=kwargs, **options)
            )

    def apply(self, args=None, kwargs=None, **options):
        if 'retries' in options:
            return super().apply(args=args, kwargs=kwargs, **options)
        else:
            return self._first_apply(is_async=False, args=args, kwargs=kwargs, **options)

    def apply_async(self, args=None, kwargs=None, **options):
        app = self._get_app()
        try:
            if self.request.id or app.conf.task_always_eager:
                return super().apply_async(args=args, kwargs=kwargs, **options)
            else:
                return self._first_apply(
                    is_async=True, args=args, kwargs=kwargs, **options,
                )
        except (InterfaceError, OperationalError) as ex:
            logger.warn('Closing old database connections, following exception thrown: %s', str(ex))
            close_old_connections()
            raise ex

    def delay_on_commit(self, *args, **kwargs):
        self.apply_async_on_commit(args, kwargs)

    def on_apply_retry(self, args, kwargs, exc, eta):
        """
        On retry task is invoked before task was retried.
        :param args: task args
        :param kwargs: task kwargs
        :param exc: raised exception which caused retry
        """
        pass

    def retry(self, args=None, kwargs=None, exc=None, throw=True,
              eta=None, countdown=None, max_retries=None, default_retry_delays=None, **options):
        if (default_retry_delays or (
                max_retries is None and eta is None and countdown is None and max_retries is None
                and self.default_retry_delays)):
            default_retry_delays = self.default_retry_delays if default_retry_delays is None else default_retry_delays
            max_retries = len(default_retry_delays)
            countdown = default_retry_delays[self.request.retries] if self.request.retries < max_retries else None

        if not eta and countdown is None:
            countdown = self.default_retry_delay

        if not eta:
            eta = now() + timedelta(seconds=countdown)

        self.on_apply_retry(args, kwargs, exc, eta)

        if CELERY_VERSION < StrictVersion('4.4.3'):
            # Celery < 4.4.3 retry not working in eager mode. This simple hack fix it.
            self.request.is_eager = False

        return super().retry(
            args=args, kwargs=kwargs, exc=exc, throw=throw,
            eta=eta, max_retries=max_retries, **options
        )

    def apply_async_and_get_result(self, args=None, kwargs=None, timeout=None, propagate=True, **options):
        """
        Apply task in an asynchronous way, wait defined timeout and get AsyncResult or TimeoutError
        :param args: task args
        :param kwargs: task kwargs
        :param timeout: timout in seconds to wait for result
        :param propagate: propagate or not exceptions from celery task
        :param options: apply_async method options
        :return: AsyncResult or TimeoutError
        """
        result = self.apply_async(args=args, kwargs=kwargs, **options)
        if timeout is None or timeout > 0:
            return result.get(timeout=timeout, propagate=propagate)
        else:
            raise TimeoutError('The operation timed out.')

    def get_command_kwargs(self):
        return {}


def obj_to_string(obj):
    return base64.encodebytes(pickle.dumps(obj)).decode('utf8')


def string_to_obj(obj_string):
    return pickle.loads(base64.decodebytes(obj_string.encode('utf8')))


def get_django_command_task(command_name):
    if command_name not in current_app.tasks:
        raise ImproperlyConfigured(
            'Command was not found please check DJANGO_CELERY_EXTENSIONS_AUTO_GENERATE_TASKS_DJANGO_COMMANDS setting'
        )
    return current_app.tasks[command_name]


def auto_convert_commands_to_tasks():
    for name in get_commands():
        if name in settings.AUTO_GENERATE_TASKS_DJANGO_COMMANDS:
            def generate_command_task(command_name):
                shared_task_kwargs = dict(
                    base=import_string(settings.AUTO_GENERATE_TASKS_BASE),
                    bind=True,
                    name=command_name,
                    ignore_result=True,
                    **settings.AUTO_GENERATE_TASKS_DEFAULT_CELERY_KWARGS
                )
                shared_task_kwargs.update(settings.AUTO_GENERATE_TASKS_DJANGO_COMMANDS[command_name])

                @shared_task(
                    **shared_task_kwargs
                )
                def command_task(self, command_args=None, **kwargs):
                    command_args = [] if command_args is None else command_args
                    call_command(
                        command_name,
                        settings=os.environ.get('DJANGO_SETTINGS_MODULE'),
                        *command_args,
                        **self.get_command_kwargs()
                    )

            generate_command_task(name)
