import asyncio
import os


class AsyncExecutor:
    def __init__(self, max_concurrent=None):
        self._max_concurrent = \
            os.cpu_count() if max_concurrent is None else max_concurrent
        self._queued = []
        self._pending = set()
        self._completed = set()

    def submit(self, func, *args, **kwargs):
        event = asyncio.Event()
        task = asyncio.create_task(self._wrap(event, func, args, kwargs))
        self._queued.append((event, task))
        return task

    @staticmethod
    async def _wrap(event, func, args, kwargs):
        await event.wait()
        return await func(*args, **kwargs)

    def _fill(self):
        for _ in range(self._max_concurrent - len(self._pending)):
            if not self._queued:
                return
            event, task = self._queued.pop(0)
            event.set()
            self._pending.add(task)

    def __len__(self):
        return len(self._queued) + len(self._pending) + len(self._completed)

    def __aiter__(self):
        return self

    async def __anext__(self):
        if not len(self):
            raise StopAsyncIteration

        if not self._completed:
            self._fill()
            self._completed, self._pending = await asyncio.wait(
                self._pending, return_when=asyncio.FIRST_COMPLETED)

        return self._completed.pop()
