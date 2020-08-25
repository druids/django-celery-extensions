from django.conf import settings as django_settings

from attrdict import AttrDict

from celery.beat import DEFAULT_MAX_INTERVAL


DEFAULTS = {
    'CACHE_NAME': 'default',
    'KEY_PREFIX': 'django-celery-extensions',
    'LOCK_KEY': 'lock',
    'LOCK_TIMEOUT': DEFAULT_MAX_INTERVAL * 5,
    'LOCK_SLEEP':  DEFAULT_MAX_INTERVAL,
    'TASK_STALE_TIME_LIMIT': None,
    'TASK_STALE_TIMELIMIT_FROM_TIME_LIMIT_CONSTANT': None,
    'AUTO_GENERATE_TASKS_DJANGO_COMMANDS': {},
    'AUTO_GENERATE_TASKS_BASE': 'django_celery_extensions.task.DjangoTask',
    'AUTO_GENERATE_TASKS_DEFAULT_CELERY_KWARGS': {},
}


class Settings:

    def __getattr__(self, attr):
        if attr not in DEFAULTS:
            raise AttributeError('Invalid setting: "{}"'.format(attr))

        value = getattr(django_settings, 'DJANGO_CELERY_EXTENSIONS_{}'.format(attr), DEFAULTS[attr])

        if isinstance(value, dict):
            value = AttrDict(value)

        return value


settings = Settings()
