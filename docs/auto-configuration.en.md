# Auto-configuration

[中文](auto-configuration.md) | English

After an application installs a starter that declares an auto-configuration entry point, PythonBoot discovers and assembles its Beans by default. The third-party package does not need to be added to `scan_packages`. A database driver alone does not declare an entry point; use the corresponding starter. Definitions are registered while the application is created, while resources such as pools are initialized in ASGI lifespan and released at shutdown.

## Declare a starter entry point

Declare the entry point in the starter's `pyproject.toml`:

```toml
[project.entry-points."pythonboot.autoconfigure"]
postgres = "pythonboot_postgres.configuration:PostgresAutoConfiguration"
```

An entry can reference an `@auto_configuration` class or a module containing such classes. A starter declares its own driver dependency; PythonBoot core does not include database drivers.

The following is an `asyncpg` starter example in `pythonboot_postgres/configuration.py`:

```python
from typing import Any

from pydantic_settings import BaseSettings
from pythonboot import (
    auto_configuration, bean, conditional_on_missing_bean,
    conditional_on_module, conditional_on_property,
    configuration_properties, ondestroy, postconstruct,
)


@configuration_properties("postgres")
class PostgresProperties(BaseSettings):
    dsn: str
    min_size: int = 1
    max_size: int = 10


class DatabasePool:
    def __init__(self, properties: PostgresProperties) -> None:
        self.properties = properties
        self.pool: Any = None

    @postconstruct
    async def initialize(self) -> None:
        import asyncpg

        self.pool = await asyncpg.create_pool(
            dsn=self.properties.dsn,
            min_size=self.properties.min_size,
            max_size=self.properties.max_size,
        )

    @ondestroy
    async def shutdown(self) -> None:
        if self.pool is not None:
            await self.pool.close()


@auto_configuration(imports=(PostgresProperties,))
@conditional_on_module("asyncpg")
@conditional_on_property("postgres.enabled", having_value=True)
@conditional_on_missing_bean(DatabasePool)
class PostgresAutoConfiguration:
    @bean
    def database_pool(self, properties: PostgresProperties) -> DatabasePool:
        return DatabasePool(properties)
```

Application `application.yml`:

```yaml
postgres:
  enabled: true
  dsn: postgresql://user:password@localhost/app
  min_size: 1
  max_size: 10
```

Point the bootstrap class's `config_dir` to the YAML directory. Business services inject `DatabasePool` by type. If the application supplies a `DatabasePool` Bean or a Bean of its subclass, this configuration yields completely: neither the default pool nor its properties object is created. Import the driver in an initialization method so an unmet condition cannot cause module-import failure; never create connections during module import.

## Conditions and order

- `@conditional_on_module("asyncpg")`: enables a definition when every named module is discoverable.
- `@conditional_on_property("postgres.enabled", having_value=True)`: matches a YAML dotted path. Missing values do not match by default; `match_if_missing=True` changes that. Without `having_value`, the value must exist, be non-`None`, and not be `false`. Environment variables still bind configuration objects but are not evaluated directly by this condition.
- `@conditional_on_bean(DatabasePool, "metrics")`: enables when all named types or Beans are registered.
- `@conditional_on_missing_bean(DatabasePool)`: enables when all named types or Beans are absent. Type matching includes subclasses and does not instantiate Beans.

Conditions can decorate an auto-configuration class, its imported components, and `@bean` factories. All conditions must match. They do not affect ordinary application component scanning. Imported classes must use `@component`, `@configuration`, or `@configuration_properties`.

Application definitions are always registered first. Auto-configurations are processed by ascending `order`, then qualified class name. Bean conditions see only already registered definitions. In one configuration, definitions without Bean-existence conditions register first; the remaining factories are evaluated in declaration order. If one auto-configuration requires a Bean from another, give the former a larger `order`. A duplicate name without a missing-Bean condition never overrides an existing Bean and fails explicitly.

## Disable and exclude

The bootstrap annotation can exclude a class directly:

```python
from pythonboot import PythonBootApplication, pythonboot_application
from pythonboot_postgres.configuration import PostgresAutoConfiguration


@pythonboot_application(exclude=(PostgresAutoConfiguration,))
class Application(PythonBootApplication):
    pass
```

`exclude` accepts a sequence of classes and matches exact classes only, not subclasses. It applies to ordinary components, services, controllers, configuration-properties classes, and auto-configurations. An excluded configuration and its `@bean` factories are not registered; neither is a factory whose return type is the excluded class. Routes from excluded controllers are also omitted. Exclusion controls registration rather than module imports. Any remaining Bean depending on an excluded class reports its missing dependency normally. `Application(exclude=(...))` and `create_app(exclude=(...))` are equivalent; an explicit constructor value overrides the annotation list.

```python
application = Application(auto_configure=False)

application = Application(
    exclude_auto_configurations=(
        "pythonboot_postgres.configuration.PostgresAutoConfiguration",
    ),
)
```

Here, `Application` is the application's `PythonBootApplication` subclass. `create_app` accepts the same parameters. The exclusion list accepts a configuration class's qualified name or an entry-point name. `@pythonboot_application(exclude_auto_configurations=(...))` can also declare it, and an explicit constructor argument takes precedence. Excluding by entry-point name skips loading that entry. If the same class is also in application scan scope, exclude it by qualified class name.

All auto-configured Beans use the existing container's scope, injection, AOP, initialization, and destruction facilities. Discovery never creates resources or a global container.
