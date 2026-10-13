# PythonBoot

基于 FastAPI、借鉴 Spring Boot 的 Python 后端框架。
提供启动组合装饰器、Bean 扫描、单例／多例 IoC 容器、构造器及属性注入、生命周期管理和 AOP。

要求 Python >=3.12。依赖与开发规范见 [AGENTS.md](AGENTS.md)，
模块职责见 [架构文档](docs/architecture.md)。

项目采用 `src` 包布局，先安装项目，再启动示例：

```bash
pip install -e .
uvicorn main:app --reload
```

`examples/` 约定为基于框架的样例后端项目，启动类位于
`examples/test_application.py`，继承 `PythonBootApplication`。
启动类默认递归扫描自身所在包：

```python
from pythonboot import PythonBootApplication, pythonboot_application

@pythonboot_application
class TestApplication(PythonBootApplication):
    pass

app = TestApplication().app
```

`@pythonboot_application()` 同样支持默认扫描。启动类位于
`examples.test_application` 时，默认扫描 `examples` 及所有子包、模块。
扫描支持无 `__init__.py` 的目录，启动入口复用当前模块以避免重复创建应用。
独立脚本没有所属包时，需要显式指定扫描范围。

可通过 `@pythonboot_application(scan_packages=("a.**", "b.*"))` 覆盖默认范围，
构造参数 `scan_packages` 优先于装饰器配置；空元组关闭扫描。
普通包名 `a` 递归扫描该包，`a.*` 只匹配下一层包或模块（不递归进入），
`a.**` 匹配该包及任意深度的子包、模块，表达式可组合，例如 `a.*.service.**`。
匹配仅在表达式指定的包路径内进行，不遍历整个 Python 环境。
工厂 `create_app` 使用显式 `scan_packages`，默认不扫描。

`@component` / `@service` 声明单例组件，构造器通过类型注解注入依赖。
`@configuration` 声明配置组件，`@bean` 工厂方法通过返回类型注册 Bean。

## 配置属性

启动时通过 `config_dir` 指定配置目录，框架先读取 `application.yml`，再按其中的
`active.profile` 读取对应的 `application-{profile}.yml`；后读取的同层配置覆盖先读取的配置。
配置类继承
`BaseSettings` 并使用 `@configuration_properties` 绑定 YAML 前缀，环境变量仍优先于 YAML。

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

`HealthSettings` 会作为单例 Bean 自动注册，可通过构造器或 `autowired()` 注入。
`@controller` 声明控制器类，通过构造器注入 Service；
方法使用 `@get`、`@post`、`@put`、`@patch`、`@delete` 或 `@route` 声明路由。

```python
from pythonboot import controller, get, service

@service
class HealthService:
    def health(self) -> dict[str, str]:
        return {"status": "ok"}

@controller(prefix="/health", tags=["health"])
class HealthController:
    def __init__(self, health_service: HealthService) -> None:
        self.health_service = health_service

    @get("")
    def health(self) -> dict[str, str]:
        return self.health_service.health()
```

控制器路由支持同步和异步方法，参数与响应继续使用 FastAPI 的类型声明、
`Query`、`Body`、`Depends` 等机制，`self` 不暴露为 HTTP 参数。
扫描模块中的原生 `APIRouter` 自动注册；路由通过
`Depends(inject(ServiceType))` 获取当前应用的 Bean，也可通过 `name` 指定候选。

Bean 在 ASGI lifespan 启动时实例化。声明组件或 Bean 时，可通过
`init_method="initialize"`、`destroy_method="shutdown"` 指定同步或异步生命周期方法。
Bean 工厂必须是同步函数，外部资源在初始化方法中创建，在销毁方法中释放。
缺失依赖、重复名称、多个类型候选及无法解析的循环依赖都会明确报错。

属性注入用法：

```python
from pythonboot import autowired, controller, get

@controller(prefix="/health")
class HealthController:
    health_service: HealthService = autowired()

    @get("")
    def health(self) -> Health:
        return self.health_service.health()
```

容器只注入标记 `autowired()` 的属性，支持继承的注入属性及按名称选择：
`health_service: HealthService = autowired(name="healthService")`。
`required=False` 允许缺失 Bean 时注入 None，属性类型建议写为 `Service | None`；
重复候选或依赖 Bean 构造失败仍报错。

属性在构造器执行后、初始化钩子执行前注入，不要在 `__init__` 中访问。
没有 `__dict__` 的纯 slots 实例不支持属性注入。
Bean 在属性注入前已注册最终代理，因此支持 `A.b → B.a → A` 属性循环，
双方拿到的仍是容器中的同一实例或 AOP 代理。纯构造器循环仍不支持，
混合循环只有在被回指的 Bean 已完成构造时才能解析。

懒加载同时支持 Bean 声明和属性注入：

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

`autowired(lazy=True)` 首次读取属性时解析依赖，成功后缓存当前容器的最终实例／代理。
`@service(lazy=True)` 跳过启动时主动创建，也支持 `@component`、`@configuration`、
`@controller`、`@aspect` 及 `@bean`。要真正推迟创建，目标 Bean 需要声明 `lazy=True`，
且不能被其他非延迟依赖提前引用。属性类型和 Bean 候选仍在注入时校验。
并发首次获取在容器锁内创建，保持单例；延迟 Bean 创建后照常执行 AOP 和销毁。

同步访问可执行同步初始化。延迟 Bean 使用 async 初始化钩子时，需先异步获取：

```python
service = await request.app.state.context.aget_bean(HealthService)
```

异步获取会等待初始化完成；随后访问注入属性即可取得同一实例。
未经异步初始化直接同步访问会明确报错，不会后台启动初始化或阻塞事件循环等待。
声明懒加载不会自动解决纯构造器循环，也不要在构造或初始化过程中提前访问懒加载依赖。
实际样例中的 `HealthService` 及其注入使用默认加载方式；懒加载仅用于时间 Bean 演示。

时间单例演示：访问 `GET /lazy/time`。
`CurrentTime` 使用 `@component(lazy=True)` 注册单例组件，
Controller 通过 `current_time: CurrentTime = autowired(lazy=True)` 注入。
第一次请求时才创建组件并记录时间；后续请求的 `bean_time` 保持不变，
`request_time` 随请求变化。重启应用后，首次请求会生成新的时间单例。

`GET /lazy/prototype-time` 使用 `@component(scope="prototype")` 时间组件，
通过原生 `Depends(inject(PrototypeTime))` 每次请求重新获取，`bean_time` 随请求变化。

## Bean 参数及作用域

`@component`、`@service`、`@configuration`、`@controller`、`@aspect`、`@bean`
统一支持以下参数；`@bean` 用于工厂方法返回值，其他装饰器用于类。

| 参数 | 默认值 | 含义 |
| --- | --- | --- |
| `name` | 自动生成 | Bean 名称 |
| `scope` | `"singleton"` | `singleton` 应用级单例；`prototype` 每次获取创建 |
| `lazy` | `False` | 单例延迟创建；多例本身按需创建 |
| `primary` | `False` | 多候选时作为唯一首选 |
| `qualifiers` | `()` | 注入时使用的限定标签 |
| `depends_on` | `()` | 必须先初始化的 Bean 名称 |
| `init_method` | `None` | 实例初始化方法名 |
| `destroy_method` | `None` | 单例退出时的销毁方法名 |

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

限定符注入：`cache: Cache = autowired(qualifier="local")`。
容器 `get_bean`、`aget_bean` 和 Web `inject` 同样支持 `name`、`qualifier`。
构造器可使用 `Annotated[Cache, autowired(qualifier="local")]` 选择候选。
限定符先过滤候选；存在多个候选时仅有一个 `primary=True` 才能自动选取，
否则明确报错，不覆盖重复名称的 Bean。

`prototype` 每次 `context.get_bean(Type)` 或 `aget_bean(Type)` 创建新实例，
运行依赖注入、AOP 和初始化，容器不缓存它，也不自动执行其销毁方法，
资源由使用方负责释放。普通属性／构造器注入仅创建一次并保存该引用；
懒属性在首次访问时创建并保存引用，并非每次访问都创建。
通过 FastAPI `Depends(inject(Type))` 获取多例时，默认依赖缓存使同一请求复用，
不同请求获取新实例；需要同一请求重复解析可指定 `use_cache=False`。
多例不主动在启动时创建，纯多例循环依赖仍报错。

`depends_on` 按名称声明初始化顺序，缺失 Bean、声明循环或无法满足的初始化环
都会明确报错；普通属性循环只能保证引用已注入，不保证循环双方都先完成初始化。
`@controller` 额外保留 `prefix`、`tags` 等原生路由参数，`@aspect` 额外支持 `order`。

`configure(app)` 仍可注册原生路由、中间件和异常处理器，构造参数仍支持
FastAPI 配置及原生 `lifespan`。用户 lifespan 在容器启动后进入，并在容器销毁前退出。

样例项目按 `controller`、`service`、`config`、`domain`、`schema` 分层，
其中 `schema` 专门存放数据库模型，当前尚未引入数据库依赖。

## 初始化注解

```python
from pythonboot import autowired, component, postconstruct

@component
class Cache:
    settings: Settings = autowired()

    @postconstruct
    def initialize(self) -> None:
        self.capacity = self.settings.cache_capacity
```

`@postconstruct`（也支持 `@postconstruct()`）在依赖注入完成后自动调用，
方法只能接收 self，支持同步或 async。单例每实例执行一次，多例每个新实例执行一次；
懒加载 Bean 在首次创建时执行，异步回调仍需通过 `aget_bean` 等待。
继承回调按基类到子类执行，同名覆盖遵循 Python 方法解析规则。
多个回调按类中的声明顺序执行；先执行注解回调，再执行显式 init_method，
同一方法同时被两种方式声明时只执行一次。回调不进入 AOP 通知链。
时间演示组件的 `created_at` 已改为在 `@postconstruct` 中设置。

`@ondestroy`（也支持 `@ondestroy()`）在单例 Bean 销毁前调用，支持同步和 async。
继承回调按子类到基类执行，再执行显式 `destroy_method`；同名方法只执行一次，
且销毁回调不进入 AOP 通知链。prototype Bean 不自动执行销毁回调。

## 容器工具

```python
from pythonboot.util import ContextUtil

context = ContextUtil.get_application_context()
service = ContextUtil.get_bean_by_name("healthService")
service = ContextUtil.get_bean_by_type(HealthService)
# 同一接口也可按名称或类型获取：
service = ContextUtil.get_bean("healthService")
service = ContextUtil.get_bean(HealthService, qualifier="local")
```

请求、WebSocket 和应用 lifespan 内自动绑定当前应用容器，保持单例／多例、
懒加载及 AOP 语义。异步初始化使用 `await ContextUtil.aget_bean(TypeOrName)`。
独立任务使用 `with ContextUtil.use(application.context): ...` 显式绑定；
未绑定时明确报错，不从其他应用获取 Bean。也支持 `from pythonboot import ContextUtil`。

## AOP

切面类通过 `@aspect` 注册，支持构造器注入。

业务方法可通过自定义注解选择切面，无需匹配包路径：

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

调用容器注入的 `OrderService.create_order()` 就会触发日志切面，
未标记的方法不会匹配这个切点。所有通知装饰器均支持注解切点。
同一方法可叠加多个注解；同名注解匹配同一切点，建议在单独模块统一定义。
注解仅标记方法，不改变调用签名，仍通过容器代理执行通知。
样例在 `examples/annotations/aop_annotations.py` 定义 `logged`，
`HealthService.health()` 使用 `@logged`，`LoggingAspect` 使用 `@before(logged)`。

```python
from pythonboot import ProceedingJoinPoint, around, aspect

@aspect(order=0)
class ServiceAspect:
    @around("examples.service.**")
    def invoke(self, join_point: ProceedingJoinPoint):
        result = join_point.proceed()
        return result
```

切点匹配 `模块.类.方法` 全限定名：`examples.service.**` 匹配所有服务方法，
`examples.service.*.*.health` 匹配指定层级的 health 方法。
`*` 匹配一层，`**` 匹配任意层级。可复用 `pointcut("examples.service.**")`，
也可传入 `lambda method: method.bean_name == "healthService"` 等谓词。

通知参数约定：

| 通知 | 方法签名 | 执行时机 |
| --- | --- | --- |
| `@before(cut)` | `(self, join_point)` | 调用前 |
| `@after(cut)` | `(self, join_point)` | 退出时，无论成功或异常 |
| `@after_returning(cut)` | `(self, join_point, result)` | 成功返回后 |
| `@after_throwing(cut)` | `(self, join_point, error)` | 抛出异常后，继续传播异常 |
| `@around(cut)` | `(self, join_point)` | 包围调用，可修改参数、结果或处理异常 |

普通通知的返回值被忽略，只有环绕通知的返回值作为调用结果。
`JoinPoint` 提供 `bean_name`、`target`、`method`、`args`、`kwargs` 及
`qualified_name`。环绕通知使用 `proceed()` 沿用参数，或 `proceed(*args, **kwargs)`
替换全部参数，可调用多次或不调用以短路目标方法。

异步目标的环绕通知通常写为：

```python
@around("myapp.service.**")
async def invoke(self, join_point: ProceedingJoinPoint):
    return await join_point.proceed()
```

异步目标支持同步及异步通知；同步目标只支持同步通知，禁止返回 awaitable。
切面 `order` 优先，其次为通知装饰器的 `order`，数值越小越先进入，
退出通知按嵌套链反向执行；相同顺序按 Bean 名、通知方法名稳定排序。
异常通知观察其内层调用抛出的异常；通知自身抛出的异常也会向外传播。
切面自身、生命周期方法、私有方法、静态／类方法不增强。
匹配到生成器方法时明确报错。同一 Bean 内部 `self.method()` 调用不会触发 AOP，
通过容器注入的其他 Bean 调用会触发。样例切面位于 `examples/config/logging_aspect.py`。

也可以使用启动类启动：

```bash
python -m examples.test_application
```

默认监听 `127.0.0.1:8000`，`run()` 支持设置 `host`、`port` 和 `log_level`。
样例提供 `GET /health`。热重载使用 `uvicorn main:app --reload`。
