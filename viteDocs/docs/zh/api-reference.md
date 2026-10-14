# 完整 API 参数

本页汇总核心公开 API 参数。

## 启动与容器

| API | 参数 |
| --- | --- |
| `ApplicationContext(definitions=(), configuration=None)` | Bean 定义序列与配置映射 |
| `get_bean` / `aget_bean` | `bean_type`（类或 Bean 名）、`name=None`、`qualifier=None` |
| `ContextUtil.get_bean` / `aget_bean` | 同上；另有 `get_bean_by_name(name)`、`get_bean_by_type(type, qualifier=None)`、`use(context)` |

## Bean 声明与生命周期

`component`、`service`、`configuration`、`bean` 统一参数：`name=None`、`init_method=None`、`destroy_method=None`、`lazy=False`、`scope="singleton"`、`primary=False`、`qualifiers=()`、`depends_on=()`。`bean(factory=None, *, ...)` 可写为裸装饰器或带参数装饰器。

`autowired(*, name=None, required=True, lazy=False, qualifier=None)` 返回属性描述器。`postconstruct(method=None)`、`ondestroy(method=None)` 没有候选参数。`Scope` 仅支持 `singleton`、`prototype`。

## AOP

| API | 参数 |
| --- | --- |
| `aspect` | 通用 Bean 参数 + `order=0` |
| `before/after/after_returning/after_throwing/around` | `cut`、`order=0` |
| `pointcut` | 字符串路径、`MethodAnnotation` 或 `Callable[[MethodInfo], bool]` |
| `annotation` | 非空名称字符串 |

## 配置与自动配置

| API | 参数 |
| --- | --- |
| `configuration_properties` | 点分 `prefix` |
| `auto_configuration` | `order=0`、`imports=()`（类元组） |
| `conditional_on_module` | 一个或多个模块名 |
| `conditional_on_property` | `name`、`having_value`、`match_if_missing=False` |
| `conditional_on_bean` / `conditional_on_missing_bean` | 一个或多个类型或 Bean 名 |

## 事务与任务

`transactional(method=None, *, propagation=REQUIRED, isolation=DEFAULT, timeout=-1, read_only=False, name=None, rollback_for=(Exception,), no_rollback_for=(), transaction_manager=None)`。

`ThreadPoolTaskExecutor(*, core_pool_size=8, max_pool_size=32, queue_capacity=256, keep_alive_seconds=60, thread_name_prefix="pythonboot-task-", allow_core_thread_timeout=False, rejection_policy=ABORT, wait_for_tasks_to_complete_on_shutdown=True, await_termination_seconds=None, task_decorator=None)`；`shutdown(wait=True, *, cancel_futures=False)`。
