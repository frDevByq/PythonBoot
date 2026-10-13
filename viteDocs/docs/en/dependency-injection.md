# Dependency injection / Autowired

PythonBoot supports constructor injection and explicit attribute injection. `autowired()` attribute injection is the recommended style. Both resolve by type and support names, qualifiers, primary beans, and optional dependencies.

## Constructor injection: supported alternative

Constructor injection remains supported when attribute declarations are unsuitable. Prefer `autowired()` for ordinary business components. Every injected parameter needs a concrete type annotation.

```python
from pythonboot import service

@service
class OrderService:
    def __init__(self, repository: OrderRepository, clock: Clock) -> None:
        self.repository = repository
        self.clock = clock
```

Use `Annotated` and `autowired()` to select a candidate when a type has multiple beans:

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

With a Python default value, a missing bean leaves that default intact. `Annotated[..., autowired(required=False)]` injects `None` when no candidate exists. Constructor injection does not allow `lazy=True`, positional-only parameters, `*args`, or `**kwargs`.

## Recommended: attribute injection with `autowired()`

`autowired()` must be paired with a type annotation; ordinary untyped attributes are never injected.

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

| Parameter | Type and default | Effect |
| --- | --- | --- |
| `name` | `str \| None = None` | Select an exact bean name. |
| `qualifier` | `str \| None = None` | Filter by bean name or a value declared in `qualifiers`. |
| `required` | `bool = True` | Raise `MissingBeanError` when absent; `False` injects `None`. |
| `lazy` | `bool = False` | Resolve only on first attribute read. Attribute injection only. |

`name` and `qualifier` may be combined and both filter candidates. A lazy lookup still honors scope, AOP proxying, and candidate rules. A lazy bean that is never read is never created or destroyed.

## Candidate selection

1. Collect beans assignable to the requested type.
2. Filter by `name` and/or `qualifier`.
3. Inject the sole candidate.
4. With multiple candidates, inject the only `primary=True` bean.
5. Otherwise raise `MissingBeanError` or `DuplicateBeanError`.

`T | None` / `Optional[T]` resolves candidates as `T`; `Annotated[T, autowired(...)]` keeps `T` and adds metadata. Constructor cycles fail explicitly. Singleton attribute cycles can resolve. Do not access an attribute-injected field inside `__init__`: attributes are injected after instance creation and proxy construction.

## Spring equivalent

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

`autowired(qualifier="readonly")` maps to `@Autowired` plus `@Qualifier`. PythonBoot never auto-injects ordinary class attributes.
