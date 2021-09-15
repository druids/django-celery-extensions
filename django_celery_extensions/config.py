from django.conf import settings as django_settings

from attrdict import AttrDict

from celery.beat import DEFAULT_MAX_INTERVAL


DEFAULTS = {
    'CACHE_NAME': 'default',
    'UNIQUE_TASK_KEY_PREFIX': 'django-celery-extensions|unique',
    'IGNORE_TASK_AFTER_SUCCESS_KEY_PREFIX': 'django-celery-extensions|ignore-after-success',
    'BEATER_LOCK_KEY': 'django-celery-extensions|lock',
    'LOCK_TIMEOUT': DEFAULT_MAX_INTERVAL * 5,
    'LOCK_SLEEP':  DEFAULT_MAX_INTERVAL,
    'DEFAULT_TASK_STALE_TIME_LIMIT': None,
    'DEFAULT_TASK_MAX_QUEUE_WAITING_TIME': None,
    'AUTO_GENERATE_TASKS_DJANGO_COMMANDS': {},
    'AUTO_GENERATE_TASKS_DEFAULT_CELERY_KWARGS': None,
    'AUTO_SQS_MESSAGE_GROUP_ID': False,
    'CELERY_TASK_CHECKER': None,
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
