from django.core.checks import register, Tags

import import_string

from .config import settings


@register(Tags.async_support)
def check_celery_tasks(app_configs, **kwargs):
    from celery import current_app

    errors = []

    if settings.CELERY_TASK_CHECKER:
        checker = import_string(settings.CELERY_TASK_CHECKER)

        for task_name, task in current_app.tasks.items():
            if not task_name.startswith('celery.'):
                error = checker(task_name, task)
                if error:
                    errors.append(error)

    return errors
