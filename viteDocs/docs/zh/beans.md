# Bean、注入与生命周期

## 声明 Bean

`@component`、`@service`、`@configuration` 修饰类；`@bean` 修饰模块函数或配置类实例方法。工厂必须为同步函数，并有具体返回类型。

```python
from typing import Annotated
from pythonboot import bean, configuration, service, autowired, postconstruct, ondestroy

@service(name="mailService", qualifiers=("notification",), primary=True)
class MailService:
    @postconstruct
    async def connect(self) -> None: ...

    @ondestroy
    async def disconnect(self) -> None: ...

@configuration
class InfraConfiguration:
    @bean(name="clock", scope="singleton")
    def clock(self) -> Clock:
        return SystemClock()

@service
class NoticeService:
    mail: MailService = autowired(qualifier="notification")

    def __init__(self, clock: Clock) -> None:
        self.clock = clock
```

全部组件装饰器的候选参数相同：

| 参数 | 说明 |
| --- | --- |
| `name: str \| None` | Bean 名；默认类名/工厂名首字母小写 |
| `scope: "singleton" \| "prototype"` | 单例按应用缓存；多例每次获取创建，不主动创建或自动销毁 |
| `lazy: bool` | 延迟 Bean 不在启动时主动创建；首次获取才创建 |
| `primary: bool` | 多个类型候选中唯一首选 |
| `qualifiers: tuple[str, ...]` | 候选标签，可去重 |
| `depends_on: tuple[str, ...]` | 先初始化的 Bean 名；缺失或形成环会报错 |
| `init_method` / `destroy_method` | 同步或异步实例方法名；分别在注入后、关闭前调用 |

`@postconstruct` / `@ondestroy` 只能标注仅接收 `self` 的实例方法。初始化顺序为基类到子类的 `@postconstruct`，再执行 `init_method`；销毁按逆创建顺序，且继承回调由子类到基类。生命周期方法不进入 AOP。

## 构造器、属性与候选解析

构造器参数必须有类型注解。多候选时先按 `qualifier` / `name` 过滤，再选择唯一 `primary`，否则报歧义。参数可用 `Annotated` 指定注入元数据：

```python
from typing import Annotated
from pythonboot import autowired, service

@service
class CheckoutService:
    def __init__(self, gateway: Annotated[PaymentGateway, autowired(name="stripe")]) -> None:
        self.gateway = gateway
```

属性注入必须同时具备类型和 `autowired()`。其参数为 `name=None`、`qualifier=None`、`required=True`、`lazy=False`；`required=False` 找不到 Bean 时注入 `None`，`lazy=True` 首次访问才解析。延迟构造器注入不支持。构造器中不能访问尚未注入的属性。属性循环可解析，纯构造器循环与多例循环会报错。

## 获取 Bean

```python
from pythonboot import ContextUtil

service = ContextUtil.get_bean(NoticeService, qualifier="primary")
clock = ContextUtil.get_bean_by_name("clock")
service = await ContextUtil.aget_bean(NoticeService)
```

`ApplicationContext.get_bean` / `aget_bean` 参数为 `bean_type`（类或名称）、`name=None`、`qualifier=None`。`ContextUtil.use(context)` 为独立任务临时绑定容器；请求和 lifespan 已自动绑定。

## Spring Boot 对照

```java
@Service("mailService") @Primary @Qualifier("notification")
class MailService {
  @PostConstruct void connect() {}
  @PreDestroy void disconnect() {}
}
@Service
class NoticeService {
  private final Clock clock;
  @Autowired @Qualifier("notification") MailService mail;
  NoticeService(Clock clock) { this.clock = clock; }
}
@Configuration
class InfraConfiguration { @Bean Clock clock() { return Clock.systemUTC(); } }
```
