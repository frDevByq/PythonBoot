# 线程池任务执行

[English](task-execution.en.md) | 中文

框架参考 Spring Boot 的 `TaskExecutor`、`ThreadPoolTaskExecutor` 设计，默认自动注册
名为 `applicationTaskExecutor` 的应用级单例 Bean。用户声明任意 `TaskExecutor` Bean
或同名 Bean 时默认执行器退让。`auto_configure=False` 会关闭自动配置。

## 注入与提交

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

`submit()` 返回标准库 `concurrent.futures.Future`，异常通过 Future 传递。
`execute()` 提交无需返回值的任务，未处理异常写入日志。
`asubmit()` 用于异步调用端等待同步任务，避免阻塞事件循环。
执行器只接受同步任务；异步函数或返回 awaitable 的任务明确报错。
`caller_runs` 策略可能在提交线程直接执行任务，异步调用端使用该策略时也可能阻塞事件循环。

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

以上为默认值，配置前缀为 `pythonboot.task.execution`。设置 `enabled: false` 关闭默认执行器。
设置类支持环境变量覆盖，例如 `PYTHONBOOT_TASK_EXECUTION_CORE_POOL_SIZE=4`。
`enabled` 是装配条件，使用 YAML 配置。

任务优先创建核心线程，然后进入队列；队列满时扩容至最大线程数，之后执行拒绝策略。
线程按需创建；超过核心数量的空闲线程在保活时间后释放。
启用 `allow_core_thread_timeout` 后核心线程也可释放。
`queue_capacity: null` 为无界队列，通常不会扩容超过核心数量；`0` 为直接交接，
有空闲线程时交给空闲线程，否则创建线程直至最大数量。

拒绝策略：`abort` 抛出 `TaskRejectedError`；`caller_runs` 在提交线程执行；
`discard` 取消新任务的 Future；`discard_oldest` 取消最老的排队任务并接纳新任务，
没有排队任务可替换时取消新任务。关闭后的提交始终抛出 `TaskRejectedError`。

## 自定义执行器

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

多个执行器使用 `primary=True` 或 `autowired(qualifier="exportExecutor")` 选择。
自定义 Bean 必须声明 `destroy_method="close"`，使容器管理线程池关闭。
也可通过 `shutdown(wait=True, cancel_futures=False)` 手动关闭。
`pool_size` 和 `queue_size` 提供当前线程数与排队任务数。

## 上下文与关闭

线程任务默认在独立 Context 中执行，不自动继承请求、事务或应用容器上下文。
需要使用容器时，在调用端获取 `ContextUtil.get_application_context()`，再在任务中
通过 `with ContextUtil.use(context)` 显式绑定。不要跨线程共享当前数据库事务。
自定义执行器支持 `task_decorator`，可包装任务执行以绑定上下文或记录日志。

应用关闭时执行异步 `close()`。默认拒绝新任务并等待已有任务全部完成；
关闭等待开关为 false 时取消排队任务，不等待运行中的任务。
`await_termination_seconds` 限制关闭等待的总时长，null 表示无限等待。
Python 无法强制终止正在运行的线程；超时返回后任务仍可能执行，非守护线程也可能延迟进程退出。
应用关闭时容器已停止提供 Bean，后台任务应提前持有所需依赖，并自行配合资源关闭。
此线程池独立于 FastAPI 自带的同步端点执行线程池。
