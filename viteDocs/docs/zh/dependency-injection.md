# 依赖注入 Autowired

PythonBoot 支持构造器注入和显式属性注入。框架推荐使用 `autowired()` 属性注入；两者都按类型查找 Bean，支持 Bean 名、限定符、首选 Bean 与可选依赖。

## 构造器注入：兼容写法

构造器注入仍然支持，适用于无法声明注入属性的场景。普通业务组件应优先使用下文的 `autowired()` 属性注入。每个需要注入的参数都必须有具体类型注解。

```python
from pythonboot import service

@service
class OrderService:
    def __init__(self, repository: OrderRepository, clock: Clock) -> None:
        self.repository = repository
        self.clock = clock
```

当某类型存在多个 Bean 时，在 `Annotated` 中使用 `autowired()` 选择候选：

```python
from typing import Annotated
from pythonboot import autowired, service

@service
class PaymentService:
    def __init__(
        self,
        gateway: Annotated[PaymentGateway, autowired(name="stripeGateway")],
        notifier: Annotated[Notifier, autowired(qualifier="email")],
    ) -> None:
        self.gateway = gateway
        self.notifier = notifier
```

构造器参数提供默认值时，未找到对应 Bean 会保留默认值；使用 `Annotated[..., autowired(required=False)]` 时，未找到 Bean 注入 `None`。构造器注入不支持 `lazy=True`，也不支持位置专用参数、`*args`、`**kwargs`。

## 推荐：属性注入 `autowired()`

`autowired()` 必须同时声明属性类型，不能用于普通未标注属性：

```python
from pythonboot import autowired, service

@service
class ReportService:
    renderer: Renderer = autowired()
    optional_cache: Cache | None = autowired(required=False)
    primary_database: Database = autowired(name="primaryDatabase")
    readonly_database: Database = autowired(qualifier="readonly")

    def render(self) -> str:
        return self.renderer.render()
```

### 参数完整说明

| 参数 | 类型与默认值 | 使用方式 |
| --- | --- | --- |
| `name` | `str \| None = None` | 精确指定 Bean 名。例如 `autowired(name="primaryDatabase")`。 |
| `qualifier` | `str \| None = None` | 按 Bean 名或其 `qualifiers` 标签过滤。例如 `autowired(qualifier="readonly")`。 |
| `required` | `bool = True` | `True` 时没有候选抛出 `MissingBeanError`；`False` 时注入 `None`。 |
| `lazy` | `bool = False` | `True` 时不在 Bean 创建期间解析；第一次读取属性时再获取目标 Bean。仅属性注入支持。 |

`name` 与 `qualifier` 可以一起使用；两项都会参与过滤。`lazy=True` 仍遵守 Bean 的作用域、AOP 代理和候选选择规则。延迟 Bean 从未被读取时不会创建，也不会执行销毁回调。

## 候选 Bean 的选择规则

1. 按类型收集可赋值的 Bean；子类实现可以注入到基类或抽象类型参数。
2. 如声明了 `name`，只保留同名 Bean；如声明了 `qualifier`，只保留同名或具有该标签的 Bean。
3. 仅剩一个候选时注入它。
4. 候选不止一个时，只有一个 `primary=True` 的 Bean 则注入它。
5. 没有候选报 `MissingBeanError`；仍不唯一报 `DuplicateBeanError`。

```python
from pythonboot import service

@service(qualifiers=("readonly",))
class ReplicaDatabase(Database):
    pass

@service(name="primaryDatabase", primary=True)
class PrimaryDatabase(Database):
    pass
```

上例中直接注入 `Database` 得到 `PrimaryDatabase`；使用 `qualifier="readonly"` 得到 `ReplicaDatabase`；使用 `name="primaryDatabase"` 得到主库。

## `Optional`、`Annotated` 与循环依赖

`T | None` / `Optional[T]` 会以 `T` 进行候选查找。`Annotated[T, autowired(...)]` 保留类型 `T` 并追加注入元数据。构造器循环依赖会明确报错；单例的属性循环依赖允许解析。不要在构造器中访问属性注入字段，因为属性注入在实例创建与最终 AOP 代理建立后执行。

## 与 Spring 的对应关系

```java
@Service
class ReportService {
    @Autowired
    @Qualifier("readonly")
    private Database database;

    private final Renderer renderer;

    ReportService(Renderer renderer) {
        this.renderer = renderer;
    }
}
```

`autowired(qualifier="readonly")` 对应字段 `@Autowired` 与 `@Qualifier`。PythonBoot 属性注入必须显式写出 `autowired()`，不会自动扫描普通类属性。
