# 自动配置

应用安装声明了自动配置入口的 starter 后，PythonBoot 默认发现并装配其 Bean，
无需把第三方包加入 `scan_packages`。普通数据库驱动本身没有入口，仍需对应 starter。
自动配置在创建应用时注册定义，连接池等资源在 ASGI lifespan 启动时初始化，关闭时释放。

## Starter 声明入口

在 starter 自己的 `pyproject.toml` 中声明：

```toml
[project.entry-points."pythonboot.autoconfigure"]
postgres = "pythonboot_postgres.configuration:PostgresAutoConfiguration"
```

入口可以指向 `@auto_configuration` 类，也可以指向包含这些类的模块。
Starter 自己声明所需驱动依赖，PythonBoot 核心不引入数据库驱动。

以下是基于 `asyncpg` 的 starter 配置示例，文件为 `pythonboot_postgres/configuration.py`：

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

应用的 `application.yml`：

```yaml
postgres:
  enabled: true
  dsn: postgresql://user:password@localhost/app
  min_size: 1
  max_size: 10
```

启动类通过 `config_dir` 指向 YAML 所在目录。业务服务按类型注入 `DatabasePool`；
应用自行提供 `DatabasePool` 或其子类的 Bean 时，上述配置整体退让，不创建默认连接池和配置对象。
驱动导入放在初始化方法中，避免未满足条件时的模块导入失败，也禁止在模块导入时创建连接。

## 条件与顺序

- `@conditional_on_module("asyncpg")`：指定模块均可发现时启用。
- `@conditional_on_property("postgres.enabled", having_value=True)`：匹配 YAML 点路径。
  默认缺失不匹配，可用 `match_if_missing=True` 修改；省略 `having_value` 时，值存在、
  非 `None` 且不是 `false` 即匹配。环境变量仍参与配置对象绑定，不直接参与此条件评估。
- `@conditional_on_bean(DatabasePool, "metrics")`：指定类型或名称均已注册时启用。
- `@conditional_on_missing_bean(DatabasePool)`：指定类型或名称均未注册时启用。
  类型匹配包含子类，不创建 Bean 实例。

条件可标记自动配置类、其 `imports` 组件和 `@bean` 工厂，多个条件同时满足才装配。
条件不作用于普通应用组件扫描。`imports` 中的类需要声明 `@component`、
`@configuration` 或 `@configuration_properties`。

应用定义始终先注册。自动配置按 `order` 从小到大，再按类全限定名排序；
Bean 条件观察此前已注册的定义，不观察未来配置。
同一配置中，无 Bean 存在性条件的定义先注册，其余按工厂声明顺序评估。
若一个自动配置需要另一个自动配置的 Bean，给前者设置较大的 `order`。
没有缺失 Bean 条件的重复名称不会自动覆盖，而是明确报错。

## 禁用与排除

启动注解支持直接按类排除：

```python
from pythonboot import PythonBootApplication, pythonboot_application
from pythonboot_postgres.configuration import PostgresAutoConfiguration


@pythonboot_application(exclude=(PostgresAutoConfiguration,))
class Application(PythonBootApplication):
    pass
```

`exclude` 接受类的序列，精确匹配指定类，不连带排除子类。
适用于普通组件、Service、Controller、配置属性类和自动配置类。
被排除的配置类及其 `@bean` 工厂均不注册；工厂返回类型等于被排除类时也不注册。
被排除 Controller 的路由同样不注册。排除只控制注册，不阻止扫描模块被导入。
其他 Bean 仍依赖已排除的类时，容器正常报告缺失依赖。
`Application(exclude=(...))` 与 `create_app(exclude=(...))` 也支持，
构造器显式传入会覆盖注解的 `exclude` 列表。

```python
application = Application(auto_configure=False)

application = Application(
    exclude_auto_configurations=(
        "pythonboot_postgres.configuration.PostgresAutoConfiguration",
    ),
)
```

这里的 `Application` 为应用自己的 `PythonBootApplication` 子类。
`create_app` 支持相同参数；排除列表接受配置类全限定名或 entry point 名称。
`@pythonboot_application(exclude_auto_configurations=(...))` 也可声明排除列表，
构造器显式传入时覆盖装饰器设置。按 entry point 名称排除会跳过该入口加载；
若同一类又出现在应用扫描范围内，使用类全限定名排除它。

所有自动配置 Bean 使用现有容器的作用域、依赖注入、AOP、初始化与销毁机制。
不新增全局容器，也不在发现入口时实例化资源。
