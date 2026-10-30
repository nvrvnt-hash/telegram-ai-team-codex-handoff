"""Process-local bounded admission. No message text is retained."""
import asyncio
import hashlib
import math
from collections import deque
from contextlib import asynccontextmanager
from dataclasses import dataclass
from time import monotonic


class LoadRejected(Exception):
    pass


@dataclass(frozen=True)
class LoadConfig:
    parallel: int = 4
    waiting: int = 16
    wait_timeout: float = 20
    run_timeout: float = 90
    user_limit: int = 6
    user_window: float = 60
    duplicate_ttl: float = 30
    update_ttl: float = 3600
    cache_limit: int = 10000

    def __post_init__(self):
        for name in ("parallel", "user_limit", "cache_limit"):
            value = getattr(self, name)
            if type(value) is not int or value < 1:
                raise ValueError(f"Invalid {name}")
        if type(self.waiting) is not int or self.waiting < 0:
            raise ValueError("Invalid waiting")
        for name in ("wait_timeout", "run_timeout", "user_window", "duplicate_ttl", "update_ttl"):
            value = getattr(self, name)
            if not math.isfinite(value) or value <= 0:
                raise ValueError(f"Invalid {name}")


class LoadControl:
    def __init__(self, config=None, clock=monotonic):
        self.config = config or LoadConfig()
        self.clock = clock
        self.running = 0
        self.operations = asyncio.Semaphore(self.config.parallel)
        self.waiters = deque()
        self.users, self.messages, self.updates, self.tasks = {}, {}, {}, {}

    def check(self, uid, text, role, update_key):
        now, c = self.clock(), self.config
        for cache in (self.messages, self.updates):
            for key, expires in list(cache.items()):
                if expires <= now:
                    cache.pop(key)
        for user, times in list(self.users.items()):
            while times and times[0] <= now - c.user_window:
                times.popleft()
            if not times:
                self.users.pop(user)
        digest = hashlib.sha256((str(role) + "\0" + " ".join(text.split())).encode()).digest()
        message_key = (uid, digest)
        if update_key is not None and update_key in self.updates:
            raise LoadRejected("Этот Telegram update уже обработан.")
        if message_key in self.messages:
            raise LoadRejected("Повторный одинаковый запрос. Подождите немного.")
        if len(self.users.get(uid, ())) >= c.user_limit:
            raise LoadRejected("Лимит запросов пользователя достигнут. Повторите позднее.")
        if any(len(cache) >= c.cache_limit for cache in (self.users, self.messages, self.updates)):
            raise LoadRejected("Защита нагрузки временно занята. Повторите позднее.")
        if self.running >= c.parallel and len(self.waiters) >= c.waiting:
            raise LoadRejected("Очередь заполнена. Повторите запрос позднее.")
        self.users.setdefault(uid, deque()).append(now)
        self.messages[message_key] = now + c.duplicate_ttl
        if update_key is not None:
            self.updates[update_key] = now + c.update_ttl

    def cancel_user(self, uid):
        for task in tuple(self.tasks.get(uid, ())):
            task.cancel()

    def delete_user(self, uid):
        self.users.pop(uid, None)
        for key in list(self.messages):
            if key[0] == uid:
                self.messages.pop(key)
        # Update keys contain only transport IDs; retained until TTL to prevent replay.

    def _release(self):
        self.running -= 1
        while self.waiters:
            future = self.waiters.popleft()
            if not future.done():
                self.running += 1
                future.set_result(None)
                break

    @asynccontextmanager
    async def slot(self, uid, text, role=None, update_key=None):
        self.check(uid, text, role, update_key)
        task = asyncio.current_task()
        self.tasks.setdefault(uid, set()).add(task)
        acquired, future = False, None
        try:
            if self.running < self.config.parallel:
                self.running += 1
                acquired = True
            else:
                future = asyncio.get_running_loop().create_future()
                self.waiters.append(future)
                try:
                    async with asyncio.timeout(self.config.wait_timeout):
                        await asyncio.shield(future)
                    acquired = True
                except BaseException:
                    if future.done() and not future.cancelled():
                        acquired = True
                    else:
                        future.cancel()
                        self.waiters.remove(future)
                    raise
            async with asyncio.timeout(self.config.run_timeout):
                yield
        finally:
            if acquired:
                self._release()
            self.tasks[uid].discard(task)
            if not self.tasks[uid]:
                self.tasks.pop(uid)
