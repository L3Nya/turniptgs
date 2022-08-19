import asyncio

from .config import CONCURRENT_SPLITTERS


class Task(asyncio.Future):
    def __init__(self, func, args, kwargs, _id, queue_manager: "QueueManager"):
        super().__init__()
        self.func = func
        self.args = args
        self.kwargs = kwargs
        self._in_queue = False
        self._queue_manager = queue_manager
        self._id = _id

    @property
    def id(self):
        return self._id

    @property
    def in_queue(self):
        return self._in_queue

    def get_position(self):
        f = self._queue_manager.get_first()
        return self._id - f._id if f else 0


class NotATaskQueue:
    def __init__(self, max_size):
        self._list = []
        self.max_size = max_size
        self._lock = asyncio.Lock()
        self._adders = []
        self._added = asyncio.Event()
        self._task = None
        self._finished = asyncio.Event()

    def size(self):
        return len(self._list)

    async def add(self, value: asyncio.Task):
        while self.size() > self.max_size:
            adder = asyncio.Event()
            async with self._lock:
                self._adders.append(adder)
            try:
                await adder.wait()
            except asyncio.CancelledError:
                try:
                    self._adders.remove(adder)
                except ValueError:
                    pass

        self._list.append(value)
        value.add_done_callback(lambda t: asyncio.create_task(self.remove(t)))

    async def remove(self, value):
        async with self._lock:
            self._list.remove(value)
            if self._adders:
                self._adders.pop().set()


class QueueManager:
    def __init__(self):
        self.lock = asyncio.Lock()
        self._queue = asyncio.Queue()
        self._task = None

    async def add_task(self, func, args=None, kwargs=None) -> Task:
        async with self.lock:
            task = Task(func, args or [], kwargs or {}, self._queue.qsize(), self)
            await self._queue.put(task)
            return task

    def start(self):
        self._task = asyncio.create_task(self._start())
        return self._task

    def stop(self):
        if self._task:
            self._task.cancel()

    async def _start(self):
        not_a_queue = NotATaskQueue(CONCURRENT_SPLITTERS)
        # not_a_queue.start()
        while True:
            try:
                task = await self._queue.get()
                task._in_queue = False
                coro = asyncio.create_task(task.func(*task.args, **task.kwargs))
                coro.add_done_callback(lambda _: task.set_result(_.result()))
                await not_a_queue.add(coro)
            except asyncio.CancelledError:
                break

    def get_first(self) -> Task | None:
        return self._queue._queue[0] if len(self._queue._queue) > 0 else None

    def size(self):
        return self._queue.qsize()
