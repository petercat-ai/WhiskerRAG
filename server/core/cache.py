import time
from functools import lru_cache, wraps
from typing import Any, Callable, Dict


class TTLCache:
    def __init__(self, ttl: int, maxsize: int):
        self.ttl = ttl
        self.maxsize = maxsize
        self.cache: Dict[str, tuple[Any, float]] = {}
        self._lru = lru_cache(maxsize=maxsize)

    def __call__(self, func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            cache_key = str(args) + str(kwargs)

            if cache_key in self.cache:
                result, timestamp = self.cache[cache_key]
                if time.time() - timestamp < self.ttl:
                    return result
                else:
                    del self.cache[cache_key]

            result = await func(*args, **kwargs)

            self.cache[cache_key] = (result, time.time())

            if len(self.cache) > self.maxsize:
                oldest_key = next(iter(self.cache))
                del self.cache[oldest_key]

            return result

        return wrapper
