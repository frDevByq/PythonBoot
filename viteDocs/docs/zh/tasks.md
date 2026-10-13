# 任务执行

默认自动配置会在 `pythonboot.task.execution.enabled` 未设置或为 `true` 时注册名为 `applicationTaskExecutor` 的 `ThreadPoolTaskExecutor`；若已有 `TaskExecutor` 类型或同名 Bean 则退让。

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
from pythonboot import TaskExecutor, autowired, service

@service
class ReportService:
    executor: TaskExecutor = autowired()

    async def generate(self) -> Report:
        return await self.executor.asubmit(build_report)
```

`TaskExecutor.submit(task, *args, **kwargs)` 返回 `Future`；`execute` 是记录未处理异常的 fire-and-forget；`asubmit` 等待同步任务且不阻塞事件循环。任务必须是同步可调用对象，不能是协程或返回 awaitable。

`ThreadPoolTaskExecutor` 参数：`core_pool_size=8`、`max_pool_size=32`、`queue_capacity=256`（`None` 无界、`0` 直接移交）、`keep_alive_seconds=60`、`thread_name_prefix="pythonboot-task-"`、`allow_core_thread_timeout=False`、`rejection_policy=ABORT`、`wait_for_tasks_to_complete_on_shutdown=True`、`await_termination_seconds=None`、`task_decorator=None`。拒绝策略为 `abort`（抛 `TaskRejectedError`）、`caller_runs`、`discard`、`discard_oldest`。线程池依次扩容核心线程、入队、扩容至最大，再拒绝。

## Spring Boot 对照

```java
@Bean
ThreadPoolTaskExecutor applicationTaskExecutor() {
  var executor = new ThreadPoolTaskExecutor();
  executor.setCorePoolSize(8); executor.setMaxPoolSize(32);
  executor.setQueueCapacity(256); executor.initialize(); return executor;
}
```
