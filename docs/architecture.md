# 架构

PythonBoot 以 FastAPI 为 Web 底座，核心模块与 Web 适配层分离。

创建应用时：确定启动类所在包或显式扫描范围 → 扫描应用组件和配置工厂 →
加载 YAML → 发现依赖包自动配置入口并评估条件 →
注册 Bean 元数据 → 创建应用级容器 → 注册类控制器路由及原生 APIRouter。

ASGI lifespan 启动时：解析构造器依赖 → 创建单例并注册最终 AOP 代理 →
注入显式声明的属性 → 调用初始化方法 →
进入用户 lifespan；退出时先退出用户 lifespan，再按实例创建顺序逆序销毁 Bean。

- `beans`：发现组件，生成 Bean 定义。
- `context`：管理 Bean 实例、依赖关系、作用域和销毁流程。
- `aop`：对匹配的 Bean 方法应用通知和代理。
- `config`：读取配置并绑定属性。
- `web`：将容器能力接入 FastAPI。
- `boot`：编排上述模块，提供 `create_app` 和 `PythonBootApplication` 启动类。
- `util`：提供 `ContextUtil`，获取当前容器以及按名称或类型获取 Bean。

`@pythonboot_application` 与 `PythonBootApplication` 组合使用，
默认递归扫描启动类所在包，支持 `scan_packages` 覆盖默认范围。
`@pythonboot_application(exclude=(SomeClass,))` 按类精确排除注册，
统一作用于组件扫描、自动配置及 Controller 路由；排除配置类同时排除其工厂，
返回类型为被排除类的工厂也不注册。构造器和 `create_app` 支持相同 `exclude` 参数。
普通包名递归扫描，`a.*` 匹配一层，`a.**` 匹配任意层级；
从指定根包路径发现模块，支持无 `__init__.py` 的命名空间目录。
编排组件扫描、配置 Bean 和 Web 自动注册。工厂 `create_app` 使用显式 `scan_packages`。
默认启用自动配置，通过 `importlib.metadata` 发现 `pythonboot.autoconfigure` entry points，
也接受应用扫描模块内的 `@auto_configuration` 类；仅导入声明入口，不扫描整个依赖环境。
入口支持配置类或包含配置类的模块；按 `order`、类全限定名稳定排序并去重。
应用定义先注册，再逐个装配自动配置，因此缺失 Bean 条件可让用户实现覆盖默认实现。
类条件先评估，匹配后导入显式 `imports` 组件并收集工厂；模块和属性不匹配的工厂
在解析返回类型之前跳过。已有／缺失 Bean 条件只观察用户定义及先前已注册的定义，
同配置中不依赖 Bean 存在性的定义先注册，需要跨配置条件依赖时使用 `order` 指定顺序。
条件采用 AND 组合，只作用于自动配置及其导入组件和工厂，不影响普通应用组件扫描。
入口加载异常保留原因并明确报错；重复 Bean 名继续由容器拒绝。
可通过 `auto_configure=False` 关闭，或通过 `exclude_auto_configurations` 排除入口／配置类。
使用示例见 [自动配置](auto-configuration.md)。
`@component`、`@service` 和 `@configuration` 声明组件，`@bean` 声明同步工厂。
容器通过类型注解解析依赖，默认单例，每个应用持有独立实例，初始化和销毁方法支持同步与异步。
属性使用 `dependency: Dependency = autowired()` 声明，可用 `name` 指定 Bean。
注册最终代理后再解析属性依赖，循环属性可引用已创建的代理，保持代理身份一致。
属性只在构造器完成后注入，初始化钩子在所有 Bean 属性注入完成后执行。
纯构造器循环，以及需要引用尚未完成构造的 Bean 的混合循环仍明确报错。
可选属性使用 `required=False`，仅在无对应 Bean 定义时注入 None，
候选歧义和已声明 Bean 的依赖解析错误不会被忽略。

组件／工厂定义携带 `scope`、`lazy`、`primary`、`qualifiers`、`depends_on`，
启动阶段只主动解析非延迟单例定义。
延迟属性保存实例级依赖解析器，首次读取时通过当前容器获取最终 Bean 并缓存。
容器使用重入锁串行化单例创建，记录已初始化、初始化中及失败状态，
支持启动完成后的动态初始化；已创建的延迟 Bean 接入相同逆序销毁流程。
异步初始化通过 `aget_bean` 等待，异步获取串行化并允许同一任务的初始化调用重入；
普通同步属性读取不隐式执行 await，遇到异步初始化明确报错。

容器分别保存 Bean 定义和单例状态，单例提前注册最终代理以支持属性循环。
多例每次解析创建独立状态与 AOP 代理，不暴露早期引用，不放入单例缓存。
实例状态记录依赖、初始化进度和失败信息，获取时只初始化该实例及其依赖。
多例运行初始化钩子，但不接入应用关闭时的销毁流程，资源由使用方释放。
`@postconstruct` 标记的实例方法在属性注入后调用，同步／异步初始化链均支持。
按基类到子类发现有效回调，同名覆盖遵循 Python 方法解析顺序；
先执行注解回调，再执行显式 init_method，同名方法只执行一次。
回调排除在 AOP 增强之外，初始化失败继续沿用实例失败状态和启动清理流程。
`depends_on` 的名称与依赖图在注册时验证，初始化时保证显式依赖先完成；
与实际实例依赖形成无法满足的初始化环时明确报错。
按类型选取候选时先应用名称及限定符过滤，有多个候选时要求唯一 primary。
Web 层通过 `Depends(inject(...))` 桥接容器，保留 FastAPI 原生依赖功能。
纯 ASGI 中间件为请求绑定 ContextVar，lifespan 同样绑定所属容器，
同步 FastAPI 路由在线程池执行时沿用复制的上下文。工具不保存全局默认容器，
独立任务可使用 `ContextUtil.use(context)` 显式绑定，退出后恢复此前上下文。
控制器为 `@controller` 标记的单例类，Service 为 `@service` 标记的类，
控制器构造器通过类型注解注入 Service。Web 层将 `@get` 等方法路由转换为
FastAPI 路由，隐藏 `self`，在请求期间从当前应用容器获取控制器实例，
保留方法参数签名及同步/异步调用方式。
启动类保留 `configure(app)`、原生 lifespan 及 Uvicorn 启动方法。

`@aspect` 将切面注册为普通单例，可使用构造器注入依赖。每个容器创建独立
`AopEngine`，从切面方法的通知声明生成按 order 排序的通知链。
创建 Bean 时，匹配公开实例方法并通过 `wrapt.ObjectProxy` 生成代理，
依赖方直接持有代理，类定义和其他应用的实例不受影响。
同步目标使用同步通知链，异步目标等待目标方法及通知的 awaitable；
异步通知匹配同步目标时抛出 `AopError`。方法签名与元数据通过包装保留。
切面自身、初始化和销毁方法、私有方法、静态及类方法不增强。
生成器目标不支持，匹配时明确报错。同一 Bean 内部的 `self.method()` 调用绕过代理。
`annotation(name)` 定义自定义方法注解，如 `logged`。业务方法使用 `@logged`，
通知使用 `@before(logged)` 或 `@around(logged)`，代理通过方法标记匹配切点。
注解只添加元数据，保留原始签名及同步／异步类型。

`examples/` 是基于框架的样例后端项目，`test_application.py` 中的
`TestApplication` 继承启动类；`main.py` 导出该样例的 ASGI 应用。
样例按 `controller`、`service`、`config`、`domain`、`schema` 分层，
`schema` 专门存放数据库模型。启动类默认扫描 `examples` 包，复用当前启动模块，
避免以 `python -m` 启动时再次导入入口并重复创建应用。
