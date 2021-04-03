from datetime import timedelta

from unittest.mock import patch

from celery.exceptions import CeleryError, TimeoutError

from django.contrib.auth.models import User
from django.test import override_settings
from django.utils.timezone import now

from germanium.test_cases.default import GermaniumTestCase
from germanium.tools import (
    assert_equal, assert_not_raises, assert_raises, assert_is_none, assert_true, assert_is_not_none,
    capture_on_commit_callbacks
)

from freezegun import freeze_time

from app.tasks import error_task, retry_task, sum_task, unique_task

from django_celery_extensions.task import (
    get_django_command_task, default_unique_key_generator, NotTriggeredCeleryError, AsyncResultWrapper
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

    @override_settings(DJANGO_CELERY_EXTENSIONS_DEFAULT_TASK_MAX_QUEUE_WAITING_TIME=1)
    def test_stale_time_limit_should_be_computed_from_soft_time_limit_and_queue_waiting_time(self):
        assert_equal(unique_task.apply_async_and_get_result(), 'unique')

    @freeze_time(now())
    def test_task_on_invocation_apply_signal_method_was_called_with_right_input(self):
        with patch.object(sum_task, 'on_invocation_apply') as mocked_method:
            with capture_on_commit_callbacks(execute=True):
                sum_task.apply_async_on_commit(args=(8, 19), invocation_id='test')
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
                    }
                )

                sum_task.apply_async(args=(8, 19), invocation_id='test2', task_id='test2')
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
                    }
                )

    @freeze_time(now())
    def test_task_on_invocation_trigger_signal_method_was_called_with_right_input(self):
        with patch.object(sum_task, 'on_invocation_trigger') as mocked_method:
            with capture_on_commit_callbacks(execute=True):
                sum_task.apply_async_on_commit(args=(8, 19), invocation_id='test invocation', task_id='test task')
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
                        'eta': now(),
                        'countdown': None,
                        'expires': None,
                        'stale_time_limit': None,
                        'using': None,
                    }
                )

            sum_task.apply(kwargs={'a': 8, 'b': 19}, invocation_id='test invocation', task_id='test task')
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
                    'eta': now(),
                    'countdown': None,
                    'expires': None,
                    'stale_time_limit': None,
                    'using': None,
                }
            )

            with override_settings(DJANGO_CELERY_EXTENSIONS_DEFAULT_TASK_MAX_QUEUE_WAITING_TIME=1):
                sum_task.apply(kwargs={'a': 8, 'b': 19}, invocation_id='test invocation', task_id='test task')
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
                        'eta': now(),
                        'countdown': None,
                        'expires': now() + timedelta(seconds=1),
                        'stale_time_limit': 301,
                        'using': None,
                    }
                )

    @freeze_time(now())
    @override_settings(CELERY_ALWAYS_EAGER=False, DJANGO_CELERY_EXTENSIONS_DEFAULT_TASK_MAX_QUEUE_WAITING_TIME=1)
    def test_task_on_invocation_unique_signal_method_was_called_with_right_input(self):
        with patch.object(unique_task, 'on_invocation_unique') as mocked_method:
            with patch.object(unique_task, '_apply_and_get_wrapped_result'):
                unique_task.apply_async(invocation_id='test invocation', task_id='test task')
                unique_task.apply_async(invocation_id='test invocation2')
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
                        'eta': now(),
                        'countdown': None,
                        'expires': now() + timedelta(seconds=1),
                        'stale_time_limit': 301,
                        'using': None,
                    }
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
            with patch.object(unique_task, '_apply_and_get_wrapped_result') as apply_method:
                apply_method.return_value = AsyncResultWrapper(
                    'test invocation', TimeoutResult(), unique_task, None, None, {'test': 'options'}
                )

                result = unique_task.apply_async(invocation_id='test invocation', task_id='test task')
                with assert_raises(TimeoutError):
                    result.get()

                mocked_method.assert_called_with(
                    'test invocation',
                    None,
                    None,
                    'test task',
                    exc,
                    {'test': 'options'}
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
