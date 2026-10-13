# Thread-pool task execution

[中文](task-execution.md) | English

PythonBoot follows the Spring Boot `TaskExecutor` and `ThreadPoolTaskExecutor` model. It auto-registers an application-scoped singleton named `applicationTaskExecutor`. The default executor yields when the user declares any `TaskExecutor` Bean or a Bean with that name. `auto_configure=False` disables it.

## Inject and submit

```python
from concurrent.futures import Future

from pythonboot import TaskExecutor, autowired, service


@service
class ExportService:
    executor: TaskExecutor = autowired()

    def export(self, document_id: int) -> Future[str]:
        return self.executor.submit(self.build_file, document_id)

    def build_file(self, document_id: int) -> str:
        return f"export-{document_id}.csv"

    async def export_async(self, document_id: int) -> str:
        return await self.executor.asubmit(self.build_file, document_id)
```

`submit()` returns a standard-library `concurrent.futures.Future`; task exceptions are delivered through it. `execute()` submits a fire-and-forget task and logs an unhandled exception. `asubmit()` lets asynchronous callers await a synchronous task without blocking the event loop. Executors accept synchronous tasks only: an async function or a task returning an awaitable fails explicitly. With `caller_runs`, a submission can run in the calling thread, and can therefore also block an async caller's event loop.

## application.yml

```yaml
pythonboot:
  task:
    execution:
      enabled: true
      core_pool_size: 8
      max_pool_size: 32
      queue_capacity: 256
      keep_alive_seconds: 60
      thread_name_prefix: pythonboot-task-
      allow_core_thread_timeout: false
      rejection_policy: abort
      wait_for_tasks_to_complete_on_shutdown: true
      await_termination_seconds: null
```

These are the defaults under `pythonboot.task.execution`. Set `enabled: false` to disable the default executor. The settings class supports environment overrides, for example `PYTHONBOOT_TASK_EXECUTION_CORE_POOL_SIZE=4`. `enabled` is an assembly condition and is read from YAML.

Tasks create core threads first and then enter the queue. Once the queue is full, the pool grows to its maximum size, then applies its rejection policy. Threads are created on demand; idle threads exceeding the core size are released after the keep-alive time. `allow_core_thread_timeout` permits core threads to be released too. `queue_capacity: null` is an unbounded queue and normally prevents growth beyond the core size. `0` uses direct handoff: it gives work to an idle thread when possible, otherwise creates a thread until the maximum is reached.

Rejection policies are: `abort`, which raises `TaskRejectedError`; `caller_runs`, which runs on the submission thread; `discard`, which cancels the new Future; and `discard_oldest`, which cancels the oldest queued task and admits the new one. If no queued task can be replaced, `discard_oldest` cancels the new task. Submission after shutdown always raises `TaskRejectedError`.

## Custom executors

```python
from pythonboot import ThreadPoolTaskExecutor, bean, configuration


@configuration
class TaskConfiguration:
    @bean(name="exportExecutor", destroy_method="close")
    def export_executor(self) -> ThreadPoolTaskExecutor:
        return ThreadPoolTaskExecutor(
            core_pool_size=2,
            max_pool_size=8,
            queue_capacity=100,
            thread_name_prefix="export-",
        )
```

Use `primary=True` or `autowired(qualifier="exportExecutor")` when several executors exist. A custom Bean must declare `destroy_method="close"` so the container closes its thread pool. It can also be closed manually with `shutdown(wait=True, cancel_futures=False)`. `pool_size` and `queue_size` expose the current thread and queued-task counts.

## Context and shutdown

Tasks run in an independent Context and do not automatically inherit request, transaction, or application-container context. To use the container, obtain it at the call site with `ContextUtil.get_application_context()` and bind it in the task with `with ContextUtil.use(context)`. Do not share the current database transaction across threads. Custom executors accept `task_decorator` to wrap execution for context binding or logging.

Application shutdown runs asynchronous `close()`. By default it rejects new work and waits for every existing task. When the waiting switch is false, queued work is cancelled and running tasks are not awaited. `await_termination_seconds` limits the total waiting time; `null` means no limit. Python cannot forcibly stop a running thread. A task may continue after a timeout, and non-daemon threads may delay process exit. The container no longer provides Beans during shutdown, so background work should retain required dependencies beforehand and cooperate with resource closing. This thread pool is separate from FastAPI's synchronous-endpoint pool.
