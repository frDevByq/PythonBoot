# Complete API parameters

## Application and container

| API | Parameters |
| --- | --- |
| `PythonBootApplication` | `title="PythonBoot"`, `version="0.1.0"`, `scan_packages=None`, `config_dir=None`, `auto_configure=True`, `exclude_auto_configurations=None`, `exclude=None`, `**FastAPI options` |
| `create_app` | the above plus `scan_packages=()`, `exclude_modules=()`, `exclude_auto_configurations=()`, `exclude=()` |
| `pythonboot_application` | `scan_packages=None`, `exclude_auto_configurations=()`, `exclude=()` |
| `ApplicationContext` | `definitions=()`, `configuration=None` |
| `get_bean` / `aget_bean` | class or bean name, `name=None`, `qualifier=None` |

## Beans and Web

`component`, `service`, `configuration`, and `bean(factory=None, *, ...)` all accept `name=None`, `init_method=None`, `destroy_method=None`, `lazy=False`, `scope="singleton"`, `primary=False`, `qualifiers=()`, `depends_on=()`. `autowired(*, name=None, required=True, lazy=False, qualifier=None)` declares an attribute. `postconstruct(method=None)` and `ondestroy(method=None)` have no options.

`controller` accepts the same bean options plus `prefix=""`, `tags=None`, and `**APIRouter options`; `controller_advise` accepts bean options. `route(path, methods=("GET",), **FastAPI add_api_route options)` is the base of `get/post/put/patch/delete`. `exception_handler` accepts one exception class or integer status. `inject(bean_type, *, name=None, qualifier=None)`. `date_time(format)` accepts a non-empty string. `ResponseContext.redirect(url, status_code=307)` and `set_cookie(key, value, **SimpleCookie options)` configure response state.

## AOP, configuration, transactions and tasks

`aspect` has bean options plus `order=0`; every advice decorator accepts `cut, order=0`. `pointcut` accepts a string, annotation, or predicate; `annotation` accepts a non-empty name.

`configuration_properties(prefix)` accepts a dotted prefix. `auto_configuration(order=0, imports=())`; `conditional_on_module(*modules)`; `conditional_on_property(name, *, having_value=unset, match_if_missing=False)`; bean conditions accept `*types_or_names`.

`transactional(method=None, *, propagation=REQUIRED, isolation=DEFAULT, timeout=-1, read_only=False, name=None, rollback_for=(Exception,), no_rollback_for=(), transaction_manager=None)`.

`ThreadPoolTaskExecutor(*, core_pool_size=8, max_pool_size=32, queue_capacity=256, keep_alive_seconds=60, thread_name_prefix="pythonboot-task-", allow_core_thread_timeout=False, rejection_policy=ABORT, wait_for_tasks_to_complete_on_shutdown=True, await_termination_seconds=None, task_decorator=None)`; `shutdown(wait=True, *, cancel_futures=False)`.
