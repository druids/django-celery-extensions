from django.core.cache import caches
from django.core.exceptions import ImproperlyConfigured

try:
    from celery.beat import PersistentScheduler
    from celery.signals import beat_init
    from celery.utils.log import get_logger
except ImportError:
    raise ImproperlyConfigured('Missing celery library, please install it')

try:
    from redis_cache import RedisCache
except ImportError:
    raise ImproperlyConfigured('Missing redis_cache library, please install it')

from .config import settings


logger = get_logger(__name__)


class LockedPersistentScheduler(PersistentScheduler):

    lock = None
    lock_key = settings.BEATER_LOCK_KEY
    lock_timeout = settings.LOCK_TIMEOUT
    lock_sleep = settings.LOCK_SLEEP

    def tick(self, *args, **kwargs):
        if self.lock:
            logger.debug('beat: Extending lock...')
            self.lock.extend(int(self.lock_timeout), replace_ttl=True)
        res = super().tick(*args, **kwargs)
        return min(res, self.lock_sleep)

    def close(self):
        if self.lock:
            logger.debug('beat: Releasing lock...')
            self.lock.release()
            self.lock = None
        super().close()


@beat_init.connect
def acquire_distributed_beat_lock(sender=None, **kwargs):
    scheduler = sender.scheduler

    cache = caches[settings.CACHE_NAME]

    if not isinstance(cache, RedisCache):
        raise ImproperlyConfigured('Only redis cache is allowed to use LockedPersistentScheduler')

    logger.debug('beat: Acquiring lock...')
    lock = caches[settings.CACHE_NAME].lock(
        scheduler.lock_key,
        timeout=scheduler.lock_timeout,
        sleep=scheduler.lock_sleep
    )

    lock.acquire()
    scheduler.lock = lock
