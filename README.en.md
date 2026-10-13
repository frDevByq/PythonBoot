# PythonBoot

[中文](README.md) | English

PythonBoot is a FastAPI-based Python backend framework inspired by Spring Boot. It provides a composed bootstrap decorator, Bean scanning, singleton/prototype IoC containers, constructor and property injection, lifecycle management, and AOP.

Python 3.12 or later is required. See [AGENTS.md](AGENTS.md) for dependencies and development conventions, and [Architecture](docs/architecture.en.md) for module responsibilities.

The project uses a `src` layout. Install it before starting the sample:

```bash
pip install -e .
uvicorn main:app --reload
```

`examples/` is a sample backend built on the framework. Its bootstrap class is `examples/test_application.py` and extends `PythonBootApplication`. By default, a bootstrap class recursively scans its own package:

```python
from pythonboot import PythonBootApplication, pythonboot_application


@pythonboot_application
class TestApplication(PythonBootApplication):
    pass


app = TestApplication().app
```

`@pythonboot_application()` supports the same default scan. A class in `examples.test_application` scans `examples` and all subpackages and modules. Namespace directories without `__init__.py` are supported, and the bootstrap entry module is reused to avoid creating a duplicate application. Standalone scripts without a package must specify a scan scope.

Use `@pythonboot_application(scan_packages=("a.**", "b.*"))` to override the default. The constructor's `scan_packages` takes precedence; an empty tuple disables scanning. A plain package name such as `a` scans recursively; `a.*` matches only the next package or module level; `a.**` matches the package and any depth below it. Expressions can be combined, for example `a.*.service.**`. Discovery is limited to the paths specified by these expressions and never traverses the entire Python environment. The `create_app` factory uses explicit `scan_packages` and does not scan by default.

`@component` and `@service` declare singleton components. Constructor parameters are injected by type annotation. `@configuration` declares a configuration component, and a `@bean` factory registers its return type as a Bean.

## Configuration properties

Pass `config_dir` at startup to select the configuration directory. PythonBoot reads `application.yml`, then reads `application-{profile}.yml` according to `active.profile`; later values at the same level override earlier ones. A class extending `BaseSettings` and marked `@configuration_properties` binds a YAML prefix, while environment variables still take precedence over YAML.

The default log level is `INFO` with a Spring Boot-style console format. Configure the root level and named loggers in YAML:

```yaml
pythonboot:
  logging:
    level: INFO
    colors: true
    loggers:
      examples: DEBUG
```

For custom handlers, formatters, or destinations, place a standard Python `logging.config.dictConfig` configuration under `logging`; it must contain `version`. All framework configuration is under the `pythonboot` prefix.

```yaml
# application.yml
active:
  profile: dev
```

```python
from pydantic_settings import BaseSettings
from pythonboot import PythonBootApplication, configuration, configuration_properties, pythonboot_application


@configuration
@configuration_properties("health")
class HealthSettings(BaseSettings):
    status: str = "ok"


@pythonboot_application(scan_packages=("myapp",))
class Application(PythonBootApplication):
    pass


application = Application(config_dir="./config")
```

`HealthSettings` is automatically registered as a singleton Bean and can be injected through a constructor or `autowired()`.

## API documentation and controllers

By default, `/docs` serves a local full-screen Scalar API Client backed by `/openapi.json`. Use YAML to choose a documentation UI or disable docs and OpenAPI in production:

```yaml
pythonboot:
  docs:
    enabled: true
    provider: scalar # scalar, swagger, redoc
    path: /docs
    openapi_path: /openapi.json
  web:
    datetime_format: "%Y-%m-%d %H:%M:%S"
```

With `enabled: false`, neither the documentation page nor the OpenAPI endpoint is registered. `scalar` is the default API-reference UI.

Controller `datetime` path and query parameters, as well as Pydantic request-body fields, use `YYYY-MM-DD HH:mm:ss` by default. Change the format with `pythonboot.web.datetime_format`; response JSON uses the same format. An individual parameter or body field can override it:

```python
from datetime import datetime
from typing import Annotated

from fastapi import Query
from pythonboot import date_time, get


@get("/report")
def report(
    created_at: Annotated[datetime, date_time("%Y/%m/%d %H:%M:%S"), Query()],
) -> dict:
    return {"created_at": created_at}
```

Use `@controller` for controller classes and inject services through constructors. Route methods use `@get`, `@post`, `@put`, `@patch`, `@delete`, or `@route`:

```python
from pythonboot import autowired, controller, get, service


@service
class HealthService:
    def health(self) -> dict[str, str]:
        return {"status": "ok"}


@controller(prefix="/health", tags=["health"])
class HealthController:
    health_service: HealthService = autowired()

    @get("")
    def health(self) -> dict[str, str]:
        return self.health_service.health()
```

Controller routes can be synchronous or asynchronous and retain FastAPI type declarations, `Query`, `Body`, `Depends`, and other native features; `self` is not an HTTP parameter. Native `APIRouter` instances in scanned modules are registered automatically. Use `Depends(inject(ServiceType))` to resolve a Bean for the current application; `name` selects a candidate.

Beans are instantiated during ASGI lifespan. Components and Beans can name synchronous or asynchronous lifecycle methods with `init_method="initialize"` and `destroy_method="shutdown"`. Bean factories must be synchronous; external resources belong in initialization methods and are released by destruction methods. Missing dependencies, duplicate names, ambiguous type candidates, and unresolvable cycles fail explicitly.

## Property injection and lazy Beans

Use `autowired()` only on explicitly annotated properties:

```python
from pythonboot import autowired, controller, get


@controller(prefix="/health")
class HealthController:
    health_service: HealthService = autowired()

    @get("")
    def health(self) -> Health:
        return self.health_service.health()
```

Inherited injection properties are supported. Select by name with `health_service: HealthService = autowired(name="healthService")`. `required=False` injects `None` only when no Bean exists; use a type such as `Service | None`. Candidate ambiguity and a declared Bean's construction failure still fail. Properties are injected after the constructor and before initialization callbacks, so they must not be read in `__init__`. Pure `slots` instances without `__dict__` do not support property injection. Final proxies are registered first, allowing a property cycle such as `A.b → B.a → A` to reference the same instance or AOP proxy. Pure constructor cycles remain unsupported.

Both declarations and properties support lazy loading:

```python
from datetime import datetime

from pythonboot import autowired, component, controller, get


@component(lazy=True)
class TimeProvider:
    def __init__(self) -> None:
        self.created_at = datetime.now().astimezone()


@controller(prefix="/lazy")
class TimeController:
    time_provider: TimeProvider = autowired(lazy=True)

    @get("/time")
    def time(self) -> dict[str, datetime]:
        return {"bean_time": self.time_provider.created_at}
```

`autowired(lazy=True)` resolves the dependency on first property access and caches the final instance or proxy for the current container. `lazy=True` is accepted by `@service`, `@component`, `@configuration`, `@controller`, `@aspect`, and `@bean`. A target is genuinely delayed only if it is itself lazy and no non-lazy dependency refers to it. Candidate validation still occurs on injection. Concurrent first access is serialized by the container lock and preserves singleton semantics; a created lazy Bean still participates in AOP and destruction.

Synchronous access can run synchronous initialization. A lazy Bean with asynchronous initialization must be obtained first asynchronously:

```python
service = await request.app.state.context.aget_bean(HealthService)
```

This waits for initialization; later property access returns the same instance. Direct synchronous access before asynchronous initialization fails clearly instead of creating a background task or blocking the event loop. Lazy loading does not resolve constructor cycles, and a lazy dependency should not be accessed during construction or initialization.

The sample exposes `GET /lazy/time` with a `@component(lazy=True)` singleton. The first request creates it and records its time; later `bean_time` values remain unchanged while `request_time` changes. `GET /lazy/prototype-time` uses `@component(scope="prototype")` and `Depends(inject(PrototypeTime))`, so every request receives a new time Bean.

## Bean parameters and scopes

`@component`, `@service`, `@configuration`, `@controller`, `@aspect`, and `@bean` accept the following common parameters. `@bean` applies them to its factory return value; the other decorators apply them to classes.

| Parameter | Default | Meaning |
| --- | --- | --- |
| `name` | Generated | Bean name. |
| `scope` | `"singleton"` | Application singleton or a new `prototype` for every lookup. |
| `lazy` | `False` | Delay singleton creation; prototypes are already on demand. |
| `primary` | `False` | The unique preferred candidate when several exist. |
| `qualifiers` | `()` | Qualifier tags used during injection. |
| `depends_on` | `()` | Bean names that must initialize first. |
| `init_method` | `None` | Instance initialization method name. |
| `destroy_method` | `None` | Singleton destruction method name. |

```python
@component(
    name="cache", scope="singleton", lazy=True, primary=True,
    qualifiers=("local",), depends_on=("settings",),
    init_method="initialize", destroy_method="shutdown",
)
class Cache:
    def initialize(self) -> None:
        pass

    def shutdown(self) -> None:
        pass
```

Inject by qualifier with `cache: Cache = autowired(qualifier="local")`. `get_bean`, `aget_bean`, and web `inject` also accept `name` and `qualifier`. A constructor can select a candidate with `Annotated[Cache, autowired(qualifier="local")]`. Qualifiers filter candidates first; if several remain, exactly one must set `primary=True`. Duplicate Bean names are never overwritten.

Every `context.get_bean(Type)` or `aget_bean(Type)` for a `prototype` creates a new instance, runs injection, AOP, and initialization, and does not cache or destroy it automatically. The caller releases its resources. Regular constructor/property injection creates and holds one prototype reference; a lazy property does the same at first access, not on every access. FastAPI `Depends(inject(Type))` caches a prototype for one request by default; set `use_cache=False` for repeated resolution in that request. Prototypes are not created eagerly, and prototype cycles fail explicitly.

`depends_on` names an initialization order. A missing Bean, a declared cycle, or an unsatisfiable initialization cycle fails explicitly. A normal property cycle guarantees only that references have been injected, not that both sides have completed initialization. `@controller` additionally accepts native route options such as `prefix` and `tags`; `@aspect` additionally accepts `order`. `configure(app)` may still register native routes, middleware, and exception handlers. Constructor options continue to support FastAPI settings and a native lifespan; user lifespan runs after container startup and before container destruction.

## Lifecycle annotations

```python
from pythonboot import autowired, component, postconstruct


@component
class Cache:
    settings: Settings = autowired()

    @postconstruct
    def initialize(self) -> None:
        self.capacity = self.settings.cache_capacity
```

`@postconstruct` (also `@postconstruct()`) runs automatically after dependency injection. The method accepts only `self` and can be synchronous or async. It runs once for each singleton and for every new prototype; a lazy Bean runs it when first created. Async callbacks require `aget_bean` or another async initialization path. Inherited callbacks run from base to subclass and overridden names follow Python method resolution. Methods run in class declaration order; annotated callbacks run before an explicit `init_method`, and the same method runs once even if both mechanisms declare it. Callbacks do not join the AOP chain.

`@ondestroy` (also `@ondestroy()`) runs before a singleton Bean is destroyed and supports synchronous and async methods. Inherited callbacks run from subclass to base, followed by an explicit `destroy_method`; duplicate names run once. Prototype Beans do not receive automatic destruction callbacks.

## Container and request-context utilities

```python
from pythonboot.util import ContextUtil

context = ContextUtil.get_application_context()
service = ContextUtil.get_bean_by_name("healthService")
service = ContextUtil.get_bean_by_type(HealthService)
service = ContextUtil.get_bean("healthService")
service = ContextUtil.get_bean(HealthService, qualifier="local")
```

The current application container is bound automatically in requests, WebSockets, and application lifespan, preserving singleton/prototype, lazy-loading, and AOP semantics. Use `await ContextUtil.aget_bean(TypeOrName)` for asynchronous initialization. Independent tasks explicitly bind a container with `with ContextUtil.use(application.context): ...`; unbound access fails rather than reading another application's Beans. `ContextUtil` is also exported from `pythonboot`.

Services and aspects can obtain the current HTTP request with `RequestContextHolder`:

```python
from pythonboot import RequestContextHolder, service


@service
class OrderService:
    def current_user(self) -> str | None:
        request = RequestContextHolder.get_request()
        return request.headers.get("X-User-Id")
```

Use `request.query_params` and `request.path_params` for URL parameters and `await request.json()` for a JSON body. The framework caches an already-read body so it is not consumed twice. `ContextVar` isolation works for async endpoints and FastAPI's synchronous thread-pool endpoints; binding is restored at request end, and outside-request access fails. Manually created threads do not inherit the context.

Request context also offers a lock-protected data map shared by async and synchronous work in one request:

```python
RequestContextHolder.putData("user_id", 123)
user_id = RequestContextHolder.getData("user_id")
value = RequestContextHolder.getData("missing", "default")
```

Map access is thread-safe; callers must synchronize mutations inside stored mutable objects. The current response can also be changed before its headers are sent:

```python
response = RequestContextHolder.get_response()
response.status_code = 201
response.set_header("X-Trace-Id", "abc123")
response.set_cookie("session", "token", httponly=True, secure=True)
response.redirect("/login")
```

## AOP

Register an aspect class with `@aspect`; constructor injection is supported. A custom business annotation selects methods without package-path matching:

```python
from pythonboot import JoinPoint, annotation, aspect, before, service

logged = annotation("logged")


@aspect
class LoggingAspect:
    @before(logged)
    def log(self, jp: JoinPoint) -> None:
        print(jp.qualified_name)


@service
class OrderService:
    @logged
    def create_order(self) -> str:
        return "created"
```

Calling an injected `OrderService.create_order()` triggers this aspect, while unmarked methods do not match. Every advice decorator supports annotation pointcuts. Multiple annotations can be stacked; annotations with the same name match the same pointcut, so define shared annotations in one module. An annotation only marks a method and does not change its signature. The sample defines `logged` in `examples/annotations/aop_annotations.py`; `HealthService.health()` uses it and `LoggingAspect` uses `@before(logged)`.

```python
from pythonboot import ProceedingJoinPoint, around, aspect


@aspect(order=0)
class ServiceAspect:
    @around("examples.service.**")
    def invoke(self, join_point: ProceedingJoinPoint):
        result = join_point.proceed()
        return result
```

Pointcuts match the qualified `module.class.method` name. `examples.service.**` matches all service methods, while `examples.service.*.*.health` matches `health` at that exact depth. `*` matches one level and `**` any depth. Reuse `pointcut("examples.service.**")`, or pass a predicate such as `lambda method: method.bean_name == "healthService"`.

| Advice | Method signature | Timing |
| --- | --- | --- |
| `@before(cut)` | `(self, join_point)` | Before invocation. |
| `@after(cut)` | `(self, join_point)` | On exit, whether successful or exceptional. |
| `@after_returning(cut)` | `(self, join_point, result)` | After a successful return. |
| `@after_throwing(cut)` | `(self, join_point, error)` | After an exception; the exception keeps propagating. |
| `@around(cut)` | `(self, join_point)` | Around invocation; can change arguments, result, or handle errors. |

Return values from ordinary advice are ignored; only around advice supplies the call result. `JoinPoint` exposes `bean_name`, `target`, `method`, `args`, `kwargs`, and `qualified_name`. `proceed()` retains the arguments; `proceed(*args, **kwargs)` replaces all of them, and it may be called multiple times or not at all to short-circuit the target.

For an async target, around advice usually looks like:

```python
@around("myapp.service.**")
async def invoke(self, join_point: ProceedingJoinPoint):
    return await join_point.proceed()
```

Async targets accept both synchronous and asynchronous advice. Synchronous targets accept synchronous advice only and reject awaitables. Aspect `order` is considered first, then advice-decorator `order`; lower values enter first and exit in reverse nesting order. Ties are stably sorted by Bean name and advice method name. An exception advice observes errors from its inner invocation, and errors from advice also propagate. Aspects, lifecycle methods, private methods, static/class methods, and generator methods are excluded as described above. Calls to `self.method()` do not trigger AOP; calls to other container-injected Beans do. The sample aspect is `examples/config/logging_aspect.py`.

You can also start through the bootstrap class:

```bash
python -m examples.test_application
```

It listens on `127.0.0.1:8000` by default, and `run()` accepts `host`, `port`, and `log_level`. The sample provides `GET /health`; use `uvicorn main:app --reload` for hot reload.

## Global exception handling

Use `@controller_advise` to declare a global exception-handling Bean and `@exception_handler` to select an exception type or HTTP status code. The handling method receives FastAPI's native `Request` and the exception, and returns a response:

```python
from fastapi import Request
from fastapi.responses import JSONResponse
from pythonboot import controller_advise, exception_handler


@controller_advise
class GlobalExceptionHandler:
    @exception_handler(ValueError)
    def handle_value_error(self, request: Request, error: ValueError) -> JSONResponse:
        return JSONResponse(status_code=400, content={"detail": str(error)})
```
