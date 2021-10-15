from django.apps import AppConfig

from .task import auto_convert_commands_to_tasks


class DjangoCeleryExtensionsAppConfig(AppConfig):

    name = 'django_celery_extensions'
    verbose_name = 'Django celery extensions'

    def ready(self):
        auto_convert_commands_to_tasks()
        from django_celery_extensions.checks import check_celery_tasks  # noqa: F401
