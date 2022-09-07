from django.apps import AppConfig

from .task import auto_convert_commands_to_tasks, init_celery_app


class DjangoCeleryExtensionsAppConfig(AppConfig):

    name = 'django_celery_extensions'
    verbose_name = 'Django celery extensions'

    def ready(self):
        init_celery_app()
        auto_convert_commands_to_tasks()
        from django_celery_extensions.checks import check_celery_tasks  # noqa: F401
