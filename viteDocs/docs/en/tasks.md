# Task execution

The default auto-configuration registers `applicationTaskExecutor` as a `ThreadPoolTaskExecutor` when `pythonboot.task.execution.enabled` is missing or true, unless a `TaskExecutor` or same-named bean already exists.

```yaml
pythonboot:
  task:
    execution:
      enabled: true
      core_pool_size: 8
      max_pool_size: 32
      queue_capacity: 256
      rejection_policy: abort
```

```python
class ReportService:
    def __init__(self, executor: TaskExecutor): self.executor = executor
    async def generate(self): return await self.executor.asubmit(build_report)
```

`submit(task, *args, **kwargs)` returns a `Future`; `execute` is fire-and-forget with failure logging; `asubmit` awaits synchronous work without blocking the event loop. Tasks must be synchronous callables and may not return awaitables.

`ThreadPoolTaskExecutor` takes `core_pool_size=8`, `max_pool_size=32`, `queue_capacity=256` (`None` is unbounded, `0` is handoff-only), `keep_alive_seconds=60`, `thread_name_prefix="pythonboot-task-"`, `allow_core_thread_timeout=False`, `rejection_policy=ABORT`, `wait_for_tasks_to_complete_on_shutdown=True`, `await_termination_seconds=None`, and `task_decorator=None`. Rejection policies are `abort`, `caller_runs`, `discard`, and `discard_oldest`.

```java
@Bean ThreadPoolTaskExecutor applicationTaskExecutor() { var e = new ThreadPoolTaskExecutor(); e.setCorePoolSize(8); e.initialize(); return e; }
```
