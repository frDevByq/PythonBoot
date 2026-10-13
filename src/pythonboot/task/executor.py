"""Application-scoped task executors with Spring-style pool admission."""

import asyncio
import inspect
import logging
from abc import ABC, abstractmethod
from collections import deque
from collections.abc import Callable
from concurrent.futures import Future
from contextvars import Context
from enum import StrEnum
from functools import partial
from threading import Condition, Thread, current_thread
from time import monotonic
from typing import Any, ParamSpec, TypeVar

P = ParamSpec("P")
T = TypeVar("T")
TaskDecorator = Callable[[Callable[[], Any]], Callable[[], Any]]
_logger = logging.getLogger(__name__)


class TaskRejectedError(RuntimeError):
    """The executor is shut down or its pool and queue are saturated."""


class RejectionPolicy(StrEnum):
    ABORT = "abort"
    CALLER_RUNS = "caller_runs"
    DISCARD = "discard"
    DISCARD_OLDEST = "discard_oldest"


class TaskExecutor(ABC):
    """Submit synchronous work for execution outside the calling thread."""

    @abstractmethod
    def submit(self, task: Callable[P, T], /, *args: P.args, **kwargs: P.kwargs) -> Future[T]:
        """Return a future containing the task result or exception."""

    def execute(self, task: Callable[P, Any], /, *args: P.args, **kwargs: P.kwargs) -> None:
        """Submit fire-and-forget work and log unhandled task failures."""
        future = self.submit(task, *args, **kwargs)

        def report(completed: Future[Any]) -> None:
            if not completed.cancelled() and (error := completed.exception()) is not None:
                _logger.error("Task execution failed", exc_info=(type(error), error, error.__traceback__))

        future.add_done_callback(report)

    async def asubmit(self, task: Callable[P, T], /, *args: P.args, **kwargs: P.kwargs) -> T:
        """Await synchronous work without blocking the event loop."""
        return await asyncio.wrap_future(self.submit(task, *args, **kwargs))


class ThreadPoolTaskExecutor(TaskExecutor):
    """Grow core workers, enqueue work, then grow to max workers before rejecting.

    A queue capacity of None is unbounded; zero allows direct handoff only.
    Threads are created on demand. Extra workers expire after keep_alive_seconds.
    Running tasks cannot be forcibly interrupted during cancellation or shutdown.
    """

    def __init__(
        self, *, core_pool_size: int = 8, max_pool_size: int = 32,
        queue_capacity: int | None = 256, keep_alive_seconds: float = 60,
        thread_name_prefix: str = "pythonboot-task-",
        allow_core_thread_timeout: bool = False,
        rejection_policy: RejectionPolicy | str = RejectionPolicy.ABORT,
        wait_for_tasks_to_complete_on_shutdown: bool = True,
        await_termination_seconds: float | None = None,
        task_decorator: TaskDecorator | None = None,
    ) -> None:
        for name, value in (("core_pool_size", core_pool_size), ("max_pool_size", max_pool_size)):
            if isinstance(value, bool) or not isinstance(value, int) or value < 1:
                raise ValueError(f"{name} must be a positive integer")
        if max_pool_size < core_pool_size:
            raise ValueError("max_pool_size must be at least core_pool_size")
        if queue_capacity is not None and (
            isinstance(queue_capacity, bool) or not isinstance(queue_capacity, int) or queue_capacity < 0
        ):
            raise ValueError("queue_capacity must be a non-negative integer or None")
        if not 0 < keep_alive_seconds < float("inf"):
            raise ValueError("keep_alive_seconds must be positive and finite")
        if await_termination_seconds is not None and not 0 <= await_termination_seconds < float("inf"):
            raise ValueError("await_termination_seconds must be non-negative and finite or None")
        if not isinstance(thread_name_prefix, str) or not thread_name_prefix:
            raise ValueError("thread_name_prefix must be a non-empty string")
        if task_decorator is not None and not callable(task_decorator):
            raise TypeError("task_decorator must be callable")
        self.core_pool_size = core_pool_size
        self.max_pool_size = max_pool_size
        self.queue_capacity = queue_capacity
        self.keep_alive_seconds = keep_alive_seconds
        self.thread_name_prefix = thread_name_prefix
        self.allow_core_thread_timeout = allow_core_thread_timeout
        self.rejection_policy = RejectionPolicy(rejection_policy)
        self.wait_for_tasks_to_complete_on_shutdown = wait_for_tasks_to_complete_on_shutdown
        self.await_termination_seconds = await_termination_seconds
        self.task_decorator = task_decorator
        self._condition = Condition()
        self._queue: deque[tuple[Future[Any], Callable[[], Any]]] = deque()
        self._threads: set[Thread] = set()
        self._idle = 0
        self._sequence = 0
        self._shutdown = False

    @property
    def pool_size(self) -> int:
        with self._condition:
            return len(self._threads)

    @property
    def queue_size(self) -> int:
        with self._condition:
            return len(self._queue)

    def submit(self, task: Callable[P, T], /, *args: P.args, **kwargs: P.kwargs) -> Future[T]:
        if not callable(task) or inspect.iscoroutinefunction(task) or inspect.iscoroutinefunction(getattr(task, "__call__", None)):
            raise TypeError("Thread pool tasks must be synchronous callables")
        callback = partial(task, *args, **kwargs)
        if self.task_decorator is not None:
            callback = self.task_decorator(callback)
            if not callable(callback):
                raise TypeError("task_decorator must return a callable")
        future: Future[T] = Future()
        work = (future, callback)
        discarded: Future[Any] | None = None
        with self._condition:
            if self._shutdown:
                raise TaskRejectedError("Task executor has been shut down")
            if len(self._threads) < self.core_pool_size:
                self._start_worker(work)
                return future
            available = (
                self.queue_capacity is None
                or self.queue_capacity > 0 and len(self._queue) < self.queue_capacity
                or self.queue_capacity == 0 and len(self._queue) < self._idle
            )
            if available:
                self._queue.append(work)
                self._condition.notify()
                return future
            if len(self._threads) < self.max_pool_size:
                self._start_worker(work)
                return future
            if self.rejection_policy == RejectionPolicy.ABORT:
                raise TaskRejectedError("Task executor pool and queue are saturated")
            if self.rejection_policy == RejectionPolicy.DISCARD_OLDEST and self._queue:
                discarded, _ = self._queue.popleft()
                self._queue.append(work)
                self._condition.notify()
        if discarded is not None:
            discarded.cancel()
        elif self.rejection_policy == RejectionPolicy.CALLER_RUNS:
            self._run(work)
        else:
            future.cancel()
        return future

    def _start_worker(self, work: tuple[Future[Any], Callable[[], Any]]) -> None:
        self._sequence += 1
        thread = Thread(
            target=Context().run, args=(self._worker, work),
            name=f"{self.thread_name_prefix}{self._sequence}", daemon=False,
        )
        self._threads.add(thread)
        try:
            thread.start()
        except BaseException:
            self._threads.remove(thread)
            raise

    @staticmethod
    def _run(work: tuple[Future[Any], Callable[[], Any]]) -> None:
        future, callback = work
        if not future.set_running_or_notify_cancel():
            return
        try:
            result = callback()
            if inspect.isawaitable(result):
                if inspect.iscoroutine(result):
                    result.close()
                raise TypeError("Thread pool tasks must not return awaitables")
        except BaseException as error:
            future.set_exception(error)
        else:
            future.set_result(result)

    def _worker(self, work: tuple[Future[Any], Callable[[], Any]]) -> None:
        try:
            while True:
                self._run(work)
                with self._condition:
                    deadline = monotonic() + self.keep_alive_seconds
                    while not self._queue:
                        if self._shutdown:
                            self._threads.remove(current_thread())
                            return
                        may_expire = self.allow_core_thread_timeout or len(self._threads) > self.core_pool_size
                        remaining = deadline - monotonic() if may_expire else None
                        if remaining is not None and remaining <= 0:
                            self._threads.remove(current_thread())
                            return
                        self._idle += 1
                        try:
                            self._condition.wait(remaining)
                        finally:
                            self._idle -= 1
                    work = self._queue.popleft()
        finally:
            with self._condition:
                self._threads.discard(current_thread())
                self._condition.notify_all()

    def shutdown(self, wait: bool = True, *, cancel_futures: bool = False) -> None:
        """Reject new submissions, optionally cancel queued work, and join workers."""
        with self._condition:
            self._shutdown = True
            pending = tuple(self._queue) if cancel_futures else ()
            if cancel_futures:
                self._queue.clear()
            threads = tuple(self._threads)
            self._condition.notify_all()
        for future, _ in pending:
            future.cancel()
        if wait:
            deadline = (
                monotonic() + self.await_termination_seconds
                if self.await_termination_seconds is not None else None
            )
            for thread in threads:
                if thread is not current_thread():
                    thread.join(None if deadline is None else max(0, deadline - monotonic()))

    async def close(self) -> None:
        """Release workers through the container's asynchronous destruction hook."""
        await asyncio.to_thread(
            self.shutdown, self.wait_for_tasks_to_complete_on_shutdown,
            cancel_futures=not self.wait_for_tasks_to_complete_on_shutdown,
        )
