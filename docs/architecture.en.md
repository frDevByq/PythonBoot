# Architecture

[中文](architecture.md) | English

PythonBoot uses FastAPI as its web foundation and keeps the core modules separate from the web integration layer.

When an application is created, PythonBoot determines the package of the bootstrap class or uses the explicit scan scope, scans application components and configuration factories, loads YAML, discovers dependency-package auto-configuration entry points and evaluates their conditions, registers Bean metadata, creates an application-scoped container, and registers class controllers and native `APIRouter` instances.

During ASGI lifespan startup, it resolves constructor dependencies, creates singleton instances and their final AOP proxies, injects explicitly declared properties, calls initialization methods, and then enters the user lifespan. On shutdown it exits the user lifespan first and destroys Beans in reverse creation order.

- `beans`: discovers components and creates Bean definitions.
- `context`: owns Bean instances, dependencies, scopes, and destruction.
- `aop`: applies advice and proxies to matching Bean methods.
- `config`: reads configuration and binds properties.
- `web`: integrates container capabilities with FastAPI.
- `boot`: orchestrates the above modules and exposes `create_app` and `PythonBootApplication`.
- `util`: provides `ContextUtil` for accessing the current container and Beans by name or type.

`@pythonboot_application` is used with `PythonBootApplication`. It recursively scans the bootstrap package by default; `scan_packages` overrides the default scope. `exclude=(SomeClass,)` excludes exact classes consistently from component scanning, auto-configuration, and controller routes. Excluding a configuration class also excludes its factories, and a factory returning an excluded class is not registered. Constructors and `create_app` accept the same `exclude` argument.

A package name scans recursively, `a.*` matches one level, and `a.**` matches any depth. Modules are discovered only below specified package roots and namespace directories without `__init__.py` are supported. `create_app` always uses explicit `scan_packages`.

Auto-configuration is enabled by default. `importlib.metadata` discovers `pythonboot.autoconfigure` entry points; classes marked with `@auto_configuration` in scanned application modules are also accepted. Only declared entries are imported: PythonBoot never scans all installed packages. An entry can be a configuration class or a module containing configuration classes. Entries are sorted and deduplicated by `order` and qualified class name.

Application definitions are registered before auto-configuration. This lets missing-Bean conditions yield to user implementations. Class conditions are checked before explicit `imports` are loaded and factories are collected. Factories whose module or property conditions do not match are skipped before return-type resolution. Bean-existence conditions observe only user definitions and definitions registered by preceding configurations. Conditions are combined with AND and apply only to auto-configuration, its imports, and its factories. Load failures retain their cause; duplicate Bean names still fail clearly. Set `auto_configure=False` to disable it, or use `exclude_auto_configurations` to remove selected entries. See [Auto-configuration](auto-configuration.en.md).

`@component`, `@service`, and `@configuration` declare components, while `@bean` declares synchronous factories. The container resolves dependencies by type annotations. Beans are singleton by default; each application has independent instances. Initialization and destruction methods may be synchronous or asynchronous. Properties are declared explicitly with `dependency: Dependency = autowired()` and may select a Bean by `name`.

The container registers the final proxy before resolving property dependencies, so property cycles can reference the same proxy. Properties are injected only after construction; initialization callbacks run after all Bean property injection completes. Pure constructor cycles, and mixed cycles requiring a not-yet-constructed Bean, fail explicitly. Optional properties use `required=False`; only a missing definition produces `None`, while ambiguity and failures of declared dependencies are not ignored.

Component and factory definitions carry `scope`, `lazy`, `primary`, `qualifiers`, and `depends_on`. Startup eagerly resolves only non-lazy singletons. A lazy property holds an instance-level resolver and caches the final Bean after its first access. The container serializes singleton creation with a reentrant lock, records initialized, initializing, and failed states, and supports dynamic initialization after startup. Created lazy Beans join the same reverse-order destruction process. `aget_bean` coordinates asynchronous initialization; ordinary synchronous property access never performs an implicit await.

The container keeps Bean definitions and singleton state separately. Singletons expose their final proxies early to support property cycles. Every prototype resolution creates separate state and a separate AOP proxy; it is not cached and has no early reference. Prototype initialization callbacks run, but prototypes are not destroyed automatically at application shutdown. `@postconstruct` methods run after property injection, from base class to subclass, before an explicit `init_method`; duplicate callback names run only once. `depends_on` names and dependency graphs are validated during registration. Type resolution applies name and qualifier filters first, then requires a single `primary` candidate when several remain.

The web layer bridges the container with `Depends(inject(...))` while preserving FastAPI dependencies. Pure ASGI middleware binds the container with `ContextVar` for both requests and lifespan; FastAPI synchronous routes retain the copied context in their thread pool. There is no global fallback container. Independent tasks can bind one with `ContextUtil.use(context)`. Controllers are singleton classes marked `@controller`; route decorators such as `@get` are converted to FastAPI routes without exposing `self` as an HTTP parameter. The bootstrap class still supports `configure(app)`, a native lifespan, and Uvicorn startup.

`@aspect` registers an aspect as an ordinary singleton and supports constructor injection. Each container builds its own `AopEngine`, which collects advice and orders it by `order`. Matching public instance methods are proxied with `wrapt.ObjectProxy`; class definitions and instances in other applications are unchanged. Synchronous targets use a synchronous chain. Asynchronous targets await target methods and awaitable advice; awaitable advice for a synchronous target raises `AopError`. Aspect methods, lifecycle methods, private methods, static methods, and class methods are not enhanced. Generators are unsupported. Calls such as `self.method()` bypass the proxy.

`annotation(name)` creates reusable business annotations. A method marked with `@logged`, for example, can be matched by `@before(logged)` or `@around(logged)`. Annotations only add metadata and preserve the original signature and sync/async kind.

`examples/` is a framework sample, not framework test code. Its `TestApplication` extends the bootstrap class and `main.py` exports its ASGI application. The sample is layered into `controller`, `service`, `config`, `domain`, and `schema`; `schema` is reserved for database models.
