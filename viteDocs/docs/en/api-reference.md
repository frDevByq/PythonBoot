# Complete API parameters

This page lists core public API parameters.

## Application and container

| API | Parameters |
| --- | --- |
| `ApplicationContext` | `definitions=()`, `configuration=None` |
| `get_bean` / `aget_bean` | class or bean name, `name=None`, `qualifier=None` |

## Beans

`component`, `service`, `configuration`, and `bean(factory=None, *, ...)` all accept `name=None`, `init_method=None`, `destroy_method=None`, `lazy=False`, `scope="singleton"`, `primary=False`, `qualifiers=()`, `depends_on=()`. `autowired(*, name=None, required=True, lazy=False, qualifier=None)` declares an attribute. `postconstruct(method=None)` and `ondestroy(method=None)` have no options.

## AOP, configuration, transactions and tasks

`aspect` has bean options plus `order=0`; every advice decorator accepts `cut, order=0`. `pointcut` accepts a string, annotation, or predicate; `annotation` accepts a non-empty name.

`configuration_properties(prefix)` accepts a dotted prefix. `auto_configuration(order=0, imports=())`; `conditional_on_module(*modules)`; `conditional_on_property(name, *, having_value=unset, match_if_missing=False)`; bean conditions accept `*types_or_names`.

`transactional(method=None, *, propagation=REQUIRED, isolation=DEFAULT, timeout=-1, read_only=False, name=None, rollback_for=(Exception,), no_rollback_for=(), transaction_manager=None)`.

`ThreadPoolTaskExecutor(*, core_pool_size=8, max_pool_size=32, queue_capacity=256, keep_alive_seconds=60, thread_name_prefix="pythonboot-task-", allow_core_thread_timeout=False, rejection_policy=ABORT, wait_for_tasks_to_complete_on_shutdown=True, await_termination_seconds=None, task_decorator=None)`; `shutdown(wait=True, *, cancel_futures=False)`.
