from celery.exceptions import CeleryError, TimeoutError

from django.contrib.auth.models import User
from django.test import override_settings

from germanium.test_cases.default import GermaniumTestCase
from germanium.tools import assert_equal, assert_not_raises, assert_raises, assert_is_none, assert_true

from app.tasks import error_task, retry_task, sum_task, unique_task

from django_celery_extensions.task import get_django_command_task, default_unique_key_generator


class DjangoCeleryExtensionsTestCase(GermaniumTestCase):

    @override_settings(DJANGO_CELERY_EXTENSIONS_TASK_STALE_TIME_LIMIT=None)
    def test_unique_task_shoud_have_set_stale_limit(self):
        with assert_raises(CeleryError):
            unique_task.delay()
        with override_settings(DJANGO_CELERY_EXTENSIONS_TASK_STALE_TIME_LIMIT=10):
            with assert_not_raises(CeleryError):
                unique_task.delay()

    @override_settings(DJANGO_CELERY_EXTENSIONS_TASK_STALE_TIME_LIMIT=5)
    def test_apply_async_and_get_result_should_return_time_error_for_zero_timeout(self):
        with assert_raises(TimeoutError):
            unique_task.apply_async_and_get_result(timeout=0)

    @override_settings(DJANGO_CELERY_EXTENSIONS_TASK_STALE_TIME_LIMIT=5)
    def test_apply_async_and_get_result_should_return_task_result(self):
        assert_equal(unique_task.apply_async_and_get_result(), 'unique')

    def test_retry_command_should_be_retried(self):
        result = retry_task.apply_async()
        assert_equal(result.get(), 5)

    def test_apply_async_on_commit_should_run_task_and_return_none(self):
        assert_is_none(sum_task.apply_async_on_commit(args=(8, 19)))

    def test_delay_on_commit_should_run_task(self):
        assert_is_none(sum_task.delay_on_commit(8, 21))

    @override_settings(CELERY_EAGER_PROPAGATES_EXCEPTIONS=True)
    def test_delay_error_task_should_propagate_error(self):
        with assert_raises(RuntimeError):
            error_task.delay()

    @override_settings(CELERY_EAGER_PROPAGATES_EXCEPTIONS=True)
    def test_django_command_should_be_run_via_task(self):
        get_django_command_task('create_user').apply_async()
        assert_true(User.objects.exists())

    @override_settings(DJANGO_CELERY_EXTENSIONS_TASK_STALE_TIMELIMIT_FROM_TIME_LIMIT_CONSTANT=1.5)
    def test_default_unique_key_generator_should_generate_unique_id_for_same_input(self):
        assert_equal(default_unique_key_generator(unique_task, None, None), '4718e7b8-12eb-51b7-a8fb-5a98dbdf20a1')
        assert_equal(default_unique_key_generator(sum_task, None, None), '57cd2e1f-1f40-5848-a88b-ba0124e09497')
        assert_equal(default_unique_key_generator(unique_task, (), None), '4718e7b8-12eb-51b7-a8fb-5a98dbdf20a1')
        assert_equal(default_unique_key_generator(unique_task, None, {}), '4718e7b8-12eb-51b7-a8fb-5a98dbdf20a1')
        assert_equal(default_unique_key_generator(unique_task, (), {}), '4718e7b8-12eb-51b7-a8fb-5a98dbdf20a1')
        assert_equal(
            default_unique_key_generator(unique_task, ('test', ), None),
            'c89e99de-559c-5dac-b247-58ae40afc123'
        )
        assert_equal(
            default_unique_key_generator(unique_task, None, {'test': ['test', 'test']}),
            '00918486-5d65-5713-846f-7a3b75539a52'
        )

    @override_settings(DJANGO_CELERY_EXTENSIONS_TASK_STALE_TIMELIMIT_FROM_TIME_LIMIT_CONSTANT=1.5)
    def test_stale_time_limit_should_be_computed_from_soft_time_limit(self):
        assert_equal(unique_task.apply_async_and_get_result(), 'unique')
