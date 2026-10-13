# Beans, injection and lifecycle

`@component`, `@service`, and `@configuration` mark classes. `@bean` marks a module function or a configuration instance method; factories are synchronous and need a concrete return type.

```python
from pythonboot import bean, configuration, service, autowired, postconstruct, ondestroy

@service(name="mailService", qualifiers=("notification",), primary=True)
class MailService:
    @postconstruct
    async def connect(self): ...
    @ondestroy
    async def disconnect(self): ...

@configuration
class Infra:
    @bean(name="clock")
    def clock(self) -> Clock: return SystemClock()

@service
class NoticeService:
    mail: MailService = autowired(qualifier="notification")
    clock: Clock = autowired()
```

All component declarations take `name=None`, `init_method=None`, `destroy_method=None`, `lazy=False`, `scope="singleton"`, `primary=False`, `qualifiers=()`, and `depends_on=()`. A singleton is application-cached; a prototype is created per lookup, is not eagerly created, and is not automatically destroyed.

`autowired()` attribute injection is recommended. Constructor arguments require type annotations and remain supported for compatibility. Candidates are filtered by name/qualifier, then a unique primary is selected. Use `Annotated[Type, autowired(name="...")]` for constructor metadata. Attribute injection requires both a type and `autowired(name=None, required=True, lazy=False, qualifier=None)`. Missing optional attributes become `None`; lazy attributes resolve on first access. Lazy constructor injection is unsupported. Attribute cycles can resolve; constructor and prototype cycles fail.

`@postconstruct` and `@ondestroy` accept instance methods with only `self`. Postconstruct callbacks run base-to-derived before `init_method`; destroy callbacks run in reverse creation order and derived-to-base. Lifecycle methods are never advised.

`ApplicationContext.get_bean` / `aget_bean` take a class or name plus `name=None` and `qualifier=None`. `ContextUtil.use(context)` binds a container for standalone work.

```java
@Service("mailService")
@Primary
@Qualifier("notification")
class MailService {
    @PostConstruct
    void connect() {}

    @PreDestroy
    void disconnect() {}
}

@Configuration
class Infra {
    @Bean
    Clock clock() {
        return Clock.systemUTC();
    }
}
```
