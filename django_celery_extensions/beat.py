from django.core.cache import caches
from django.core.exceptions import ImproperlyConfigured

try:
    from celery.beat import PersistentScheduler
    from celery.signals import beat_init
except ImportError:
    raise ImproperlyConfigured('Missing celery library, please install it')

try:
    from redis_cache import RedisCache
except ImportError:
    raise ImproperlyConfigured('Missing redis_cache library, please install it')

from .config import settings


# Copied from:
# https://github.com/andymccurdy/redis-py/blob/master/redis/lock.py#L33
# Changes:
#     The second line from the bottom: The original Lua script intends
#     to extend time to (lock remaining time + additional time); while
#     the script here extend time to a expected expiration time.
# KEYS[1] - lock name
# ARGS[1] - token
# ARGS[2] - additional milliseconds
# return 1 if the locks time was extended, otherwise 0
LUA_EXTEND_TO_SCRIPT = """
    local token = redis.call('get', KEYS[1])
    if not token or token ~= ARGV[1] then
        return 0
    end
    local expiration = redis.call('pttl', KEYS[1])
    if not expiration then
        expiration = 0
    end
    if expiration < 0 then
        return 0
    end
    redis.call('pexpire', KEYS[1], ARGV[2])
    return 1
"""


class LockedPersistentScheduler(PersistentScheduler):

    lock = None
    lock_key = ':'.join((settings.KEY_PREFIX, settings.LOCK_KEY))
    lock_timeout = settings.LOCK_TIMEOUT
    lock_sleep = settings.LOCK_SLEEP

    def tick(self, *args, **kwargs):
        if self.lock:
            self.lock.extend(int(self.lock_timeout))
        res = super().tick(*args, **kwargs)
        return res

    def close(self):
        if self.lock:
            self.lock.release()
            self.lock = None
        super().close()


@beat_init.connect
def acquire_distributed_beat_lock(sender=None, **kwargs):
    scheduler = sender.scheduler

    cache = caches[settings.CACHE_NAME]

    if not isinstance(cache, RedisCache):
        raise ImproperlyConfigured('Only redis cache is allowed to use LockedPersistentScheduler')

    lock = caches[settings.CACHE_NAME].lock(
        scheduler.lock_key,
        timeout=scheduler.lock_timeout,
        sleep=scheduler.lock_sleep
    )

    # overwrite redis-py's extend script
    # which will add additional timeout instead of extend to a new timeout
    lock.lua_extend = lock.redis.register_script(LUA_EXTEND_TO_SCRIPT)
    lock.acquire()
    scheduler.lock = lock
