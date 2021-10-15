from datetime import timedelta

from unittest.mock import patch

from celery.exceptions import CeleryError, TimeoutError

from django.core.cache import caches
from django.contrib.auth.models import User
from django.test import override_settings
from django.utils.timezone import now

from germanium.test_cases.default import GermaniumTestCase
from germanium.tools import (
    assert_equal, assert_not_raises, assert_raises, assert_is_none, assert_true, assert_is_not_none,
    capture_on_commit_callbacks, assert_false
)

from freezegun import freeze_time

from app.tasks import (
    error_task, retry_task, sum_task, unique_task, ignored_after_success_task, ignored_after_error_task,
    task_with_fast_queue
)

from django_celery_extensions.config import settings
from django_celery_extensions.task import (
    get_django_command_task, default_unique_key_generator, NotTriggeredCeleryError
)


class DjangoCeleryExtensionsTestCase(GermaniumTestCase):

    @override_settings(DJANGO_CELERY_EXTENSIONS_DEFAULT_TASK_STALE_TIME_LIMIT=None)
    def test_unique_task_should_have_set_stale_limit(self):
        with assert_raises(CeleryError):
            unique_task.delay()
        with override_settings(DJANGO_CELERY_EXTENSIONS_DEFAULT_TASK_STALE_TIME_LIMIT=10):
            with assert_not_raises(CeleryError):
                unique_task.delay()

    @override_settings(DJANGO_CELERY_EXTENSIONS_DEFAULT_TASK_STALE_TIME_LIMIT=5)
    def test_apply_async_and_get_result_should_return_time_error_for_zero_timeout(self):
        with assert_raises(TimeoutError):
            unique_task.apply_async_and_get_result(timeout=0)

    @override_settings(DJANGO_CELERY_EXTENSIONS_DEFAULT_TASK_STALE_TIME_LIMIT=5)
    def test_apply_async_and_get_result_should_return_task_result(self):
        assert_equal(unique_task.apply_async_and_get_result(), 'unique')

    def test_apply_async_on_commit_should_run_task_and_return_on_commit_result(self):
        with capture_on_commit_callbacks(execute=True):
            result = sum_task.apply_async_on_commit(args=(8, 19))
            assert_equal(result.state, 'WAITING')
            with assert_raises(NotTriggeredCeleryError):
                result.get()
            assert_is_none(result.task_id)
        assert_equal(result.state, 'SUCCESS')
        assert_equal(result.get(), 27)
        assert_is_not_none(result.task_id)

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

    @override_settings(DJANGO_CELERY_EXTENSIONS_DEFAULT_TASK_MAX_QUEUE_WAITING_TIME=1)
    def test_default_unique_key_generator_should_generate_unique_id_for_same_input(self):
        assert_equal(
            default_unique_key_generator(unique_task, 'prefix', None, None), 'b0f110da-8416-5ab7-853b-40813c011779'
        )
        assert_equal(
            default_unique_key_generator(sum_task, 'prefix', None, None), '309a345e-7ee6-5d0b-9f61-50b6d51eb67d'
        )
        assert_equal(
            default_unique_key_generator(unique_task, 'prefix', (), None), 'b0f110da-8416-5ab7-853b-40813c011779'
        )
        assert_equal(
            default_unique_key_generator(unique_task, 'prefix', None, {}), 'b0f110da-8416-5ab7-853b-40813c011779'
        )
        assert_equal(
            default_unique_key_generator(unique_task, 'prefix', (), {}), 'b0f110da-8416-5ab7-853b-40813c011779'
        )
        assert_equal(
            default_unique_key_generator(unique_task, 'prefix', ('test', ), None),
            '06317eeb-ea14-5572-82e2-658ec53e7652'
        )
        assert_equal(
            default_unique_key_generator(unique_task, 'prefix', None, {'test': ['test', 'test']}),
            'a74865e9-7047-505c-a2ee-fda16a92e780'
        )
        assert_equal(
            default_unique_key_generator(unique_task, 'another_prefix', (), {}),
            'e5e7b393-4ee2-5053-af96-49c48a2a6855'
        )

    @override_settings(DJANGO_CELERY_EXTENSIONS_DEFAULT_TASK_MAX_QUEUE_WAITING_TIME=1)
    def test_stale_time_limit_should_be_computed_from_soft_time_limit_and_queue_waiting_time(self):
        assert_equal(unique_task.apply_async_and_get_result(), 'unique')

    @freeze_time(now())
    def test_task_on_invocation_apply_signal_method_was_called_with_right_input(self):
        with patch.object(sum_task, 'on_invocation_apply') as mocked_method:
            with capture_on_commit_callbacks(execute=True):
                result = sum_task.apply_async_on_commit(args=(8, 19), invocation_id='test')
                mocked_method.assert_called_with(
                    'test',
                    (8, 19),
                    None,
                    {
                        'queue': 'default',
                        'is_async': True,
                        'invocation_id': 'test',
                        'apply_time': now(),
                        'is_on_commit': True,
                        'using': None,
                    },
                    result
                )

                result = sum_task.apply_async(args=(8, 19), invocation_id='test2', task_id='test2')
                mocked_method.assert_called_with(
                    'test2',
                    (8, 19),
                    None,
                    {
                        'task_id': 'test2',
                        'queue': 'default',
                        'is_async': True,
                        'invocation_id': 'test2',
                        'apply_time': now(),
                        'is_on_commit': False,
                        'using': None,
                    },
                    result
                )

    @freeze_time(now())
    def test_task_on_invocation_trigger_signal_method_was_called_with_right_input(self):
        with patch.object(sum_task, 'on_invocation_trigger') as mocked_method:
            with capture_on_commit_callbacks(execute=True):
                result = sum_task.apply_async_on_commit(
                    args=(8, 19), invocation_id='test invocation', task_id='test task'
                )
                mocked_method.assert_not_called()

            mocked_method.assert_called_with(
                'test invocation',
                (8, 19),
                None,
                'test task',
                {
                    'queue': 'default',
                    'apply_time': now(),
                    'is_on_commit': True,
                    'is_async': True,
                    'invocation_id': 'test invocation',
                    'task_id': 'test task',
                    'trigger_time': now(),
                    'time_limit': 300,
                    'soft_time_limit': 120,
                    'eta': now(),
                    'countdown': None,
                    'expires': None,
                    'stale_time_limit': None,
                    'using': None,
                },
                result
            )

            result = sum_task.apply(kwargs={'a': 8, 'b': 19}, invocation_id='test invocation', task_id='test task')
            mocked_method.assert_called_with(
                'test invocation',
                None,
                {'a': 8, 'b': 19},
                'test task',
                {
                    'queue': 'default',
                    'apply_time': now(),
                    'is_on_commit': False,
                    'is_async': False,
                    'invocation_id': 'test invocation',
                    'task_id': 'test task',
                    'trigger_time': now(),
                    'time_limit': 300,
                    'soft_time_limit': 120,
                    'eta': now(),
                    'countdown': None,
                    'expires': None,
                    'stale_time_limit': None,
                    'using': None,
                },
                result
            )

            with override_settings(DJANGO_CELERY_EXTENSIONS_DEFAULT_TASK_MAX_QUEUE_WAITING_TIME=1):
                result = sum_task.apply(kwargs={'a': 8, 'b': 19}, invocation_id='test invocation', task_id='test task')
                mocked_method.assert_called_with(
                    'test invocation',
                    None,
                    {'a': 8, 'b': 19},
                    'test task',
                    {
                        'queue': 'default',
                        'apply_time': now(),
                        'is_on_commit': False,
                        'is_async': False,
                        'invocation_id': 'test invocation',
                        'task_id': 'test task',
                        'trigger_time': now(),
                        'time_limit': 300,
                        'soft_time_limit': 120,
                        'eta': now(),
                        'countdown': None,
                        'expires': now() + timedelta(seconds=1),
                        'stale_time_limit': 301,
                        'using': None,
                    },
                    result
                )

    @freeze_time(now())
    @override_settings(CELERY_ALWAYS_EAGER=False, DJANGO_CELERY_EXTENSIONS_DEFAULT_TASK_MAX_QUEUE_WAITING_TIME=1)
    def test_task_on_invocation_unique_signal_method_was_called_with_right_input(self):
        with patch.object(unique_task, 'on_invocation_unique') as mocked_method:
            with patch.object(unique_task, '_apply_and_get_result'):
                unique_task.apply_async(invocation_id='test invocation', task_id='test task')
                result = unique_task.apply_async(invocation_id='test invocation2')
                mocked_method.assert_called_with(
                    'test invocation2',
                    None,
                    None,
                    'test task',
                    {
                        'queue': 'default',
                        'apply_time': now(),
                        'is_on_commit': False,
                        'is_async': True,
                        'invocation_id': 'test invocation2',
                        'task_id': 'test task',
                        'trigger_time': now(),
                        'time_limit': 300,
                        'soft_time_limit': 120,
                        'eta': now(),
                        'countdown': None,
                        'expires': now() + timedelta(seconds=1),
                        'stale_time_limit': 301,
                        'using': None,
                    },
                    result
                )

    @freeze_time(now())
    @override_settings(CELERY_ALWAYS_EAGER=False, DJANGO_CELERY_EXTENSIONS_DEFAULT_TASK_MAX_QUEUE_WAITING_TIME=1)
    def test_task_on_invocation_timeout_signal_method_was_called_with_right_input(self):
        exc = TimeoutError('error')

        class TimeoutResult:
            task_id = 'test task'

            def get(self):
                raise exc

        with patch.object(unique_task, 'on_invocation_timeout') as mocked_method:
            with patch.object(unique_task, '_apply_and_get_result') as apply_method:
                apply_method.return_value = TimeoutResult()

                result = unique_task.apply_async(invocation_id='test invocation', task_id='test task')
                with assert_raises(TimeoutError):
                    result.get()

                mocked_method.assert_called_with(
                    'test invocation',
                    None,
                    None,
                    'test task',
                    exc,
                    result._options,
                    result
                )

    def test_task_on_task_start_signal_method_was_called_with_right_input(self):
        with patch.object(sum_task, 'on_task_start') as mocked_method:
            sum_task.apply_async(args=(1, 2), invocation_id='test invocation', task_id='test task')
            mocked_method.assert_called_with(
                'test task',
                (1, 2),
                {}
            )

    def test_task_on_task_success_signal_method_was_called_with_right_input(self):
        with patch.object(sum_task, 'on_task_success') as mocked_method:
            sum_task.apply_async(args=(1, 2), invocation_id='test invocation', task_id='test task')
            mocked_method.assert_called_with(
                'test task',
                [1, 2],
                {},
                3
            )

    def test_task_on_task_failure_signal_method_was_called_with_right_input(self):
        with patch.object(error_task, 'on_task_failure') as mocked_method:
            error_task.apply_async(invocation_id='test invocation', task_id='test task')
            mocked_method.assert_called()
            assert_equal(tuple(mocked_method.call_args[0][:3]), ('test task', (), {}))

    @freeze_time(now())
    def test_retry_command_should_be_retried(self):
        with patch.object(retry_task, 'on_task_retry') as mocked_method:
            retry_task.apply_async(task_id='test task')
            assert_equal(mocked_method.call_count, 5)

            delays = (1 * 60, 5 * 60, 10 * 60, 30 * 60, 60 * 60)
            for delay, call_args in zip(delays, mocked_method.call_args_list):
                assert_equal(
                    call_args[0], ('test task', None, None, call_args[0][3], now() + timedelta(seconds=delay))
                )

    def test_ignored_after_success_task_should_be_ignored_for_second_call(self):
        success_result = ignored_after_success_task.delay()
        assert_equal(success_result.state, 'SUCCESS')
        assert_equal(success_result.get(), 'ignored_task_after_success')

        ignored_result = ignored_after_success_task.delay()
        assert_equal(ignored_result.state, 'IGNORED')
        assert_is_none(ignored_result.get())
        assert_false(ignored_result.successful())
        assert_false(ignored_result.failed())
        assert_is_none(ignored_result.task_id)

        not_ignored_result = ignored_after_success_task.apply(ignore_task_after_success=False)
        assert_equal(not_ignored_result.state, 'SUCCESS')
        assert_equal(not_ignored_result.get(), 'ignored_task_after_success')

        with freeze_time(now() + timedelta(hours=1)):
            assert_equal(ignored_after_success_task.delay().state, 'IGNORED')

        with freeze_time(now() + timedelta(hours=1, minutes=5)):
            assert_equal(ignored_after_success_task.delay().state, 'SUCCESS')

        with freeze_time(now() + timedelta(hours=2, minutes=10)):
            ignored_after_success_task.apply(ignore_task_after_success=False)
            assert_equal(ignored_after_success_task.delay().state, 'IGNORED')

    def test_ignored_after_error_task_should_be_ignored_for_second_call(self):
        assert_equal(ignored_after_error_task.delay().state, 'FAILURE')
        assert_equal(ignored_after_error_task.delay().state, 'FAILURE')

    @freeze_time(now())
    def test_task_with_fast_queue_should_have_set_time_limit_from_queue_settings(self):
        with patch.object(task_with_fast_queue, 'on_invocation_trigger') as mocked_method:
            task_with_fast_queue.apply(invocation_id='test invocation', task_id='test task')
            mocked_method.assert_called_once()

    @override_settings(CELERY_ALWAYS_EAGER=False, DJANGO_CELERY_EXTENSIONS_DEFAULT_TASK_STALE_TIME_LIMIT=5)
    def test_unique_task_is_processing_should_return_right_value(self):
        with patch.object(unique_task, '_get_unique_key') as get_unique_key_method:
            with patch.object(unique_task, 'on_invocation_unique') as mocked_method:
                get_unique_key_method.return_value = 'unique'
                assert_false(unique_task.is_processing())
                caches[settings.CACHE_NAME].set('unique', 'random')
                assert_true(unique_task.is_processing())
                assert_equal(unique_task.apply_async().id, 'random')
                mocked_method.assert_called_once()

    def test_only_unique_task_should_use_is_processing(self):
        with assert_raises(CeleryError):
            sum_task.is_processing()
