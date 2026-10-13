# PythonBoot 开发规范

## 协作要求

- 使用中文回复，沟通简洁直接。
- 未经用户明确允许，不得自行编译、测试或运行项目，也不得安装依赖。
- 修改完成后不自行执行检查，不使用 `git diff`。
- 如涉及界面，只添加实际产品元素，不添加设计说明文字。
- 不创建 `.gitkeep` 文件，不使用占位文件保留空目录。

## 项目目标

构建基于 FastAPI 的 Python 后端框架，提供 Bean 扫描、依赖注入、
容器生命周期管理和 AOP，并保持 FastAPI 原生路由及依赖机制可用。
已提供启动组合装饰器、Bean 扫描、单例／多例容器、构造器及属性注入、生命周期管理
以及基于应用级 Bean 代理的 AOP。

## 依赖清单
本项目使用UV 管理依赖
`pyproject.toml` 是依赖声明的唯一来源；以下清单必须与其保持一致。

| 类型 | 依赖 | 版本范围 | 用途 |
| --- | --- | --- | --- |
| 运行时 | fastapi | >=0.115,<1 | ASGI Web 框架、路由和 OpenAPI |
| 运行时 | uvicorn[standard] | >=0.34,<1 | ASGI 服务及本地热重载 |
| 运行时 | pydantic | >=2.10,<3 | 数据模型与校验 |
| 运行时 | pydantic-settings | >=2.7,<3 | 环境变量和配置加载 |
| 运行时 | PyYAML | >=6,<7 | application YAML 配置文件解析 |
| 运行时 | wrapt | >=1.17,<3 | AOP 装饰器及代理基础 |
| 构建 | hatchling | >=1.27,<2 | 构建 src 布局的软件包 |

- Python 版本要求：>=3.12。
- 新增、删除、升级依赖或变更 extras 时，必须在同一次修改中同步更新
  `pyproject.toml` 和本文件的依赖清单、用途说明。
- 若后续引入锁文件，依赖变更也必须同步更新锁文件；执行生成命令前须获得用户授权。
- 新增依赖应有明确用途；标准库可以满足的功能优先使用标准库。
- 当前未引入开发或测试依赖；新增时同样登记到本文件。

## 目录与职责

```text
src/pythonboot/
  boot/          应用创建、启动流程和自动配置编排
  beans/         Bean 元数据、声明装饰器和组件扫描
  context/       IoC 容器、依赖解析、作用域和生命周期
  aop/           切面、切点、通知及代理
  web/           FastAPI 路由、依赖桥接及异常处理适配
  config/        配置模型、配置源和属性绑定
  exceptions/    框架异常
  util/          容器上下文等公共工具
examples/demo/   最小使用示例，按控制器与服务分层
tests/           基于 PythonBoot 框架的样例后端项目
  controller/    HTTP 控制器及原生 FastAPI 路由
  service/       业务服务
  config/        应用配置与配置 Bean
  domain/        业务领域对象及接口数据对象
  schema/        数据库模型
  test_application.py  样例项目启动类
docs/            架构及使用文档
main.py          本地示例 ASGI 入口
```

## 实现约定

- 框架源码 `src/pythonboot` 使用英文注释、文档字符串、日志及异常消息，不出现中文。
- Controller 必须使用类并标记 `@controller`，路由声明在实例方法上；
  Service 必须使用类并标记 `@service`，通过构造器或 `autowired()` 属性注入依赖。
- 使用绝对包导入及类型注解；需要包级公共接口时通过 `__init__.py` 显式导出。
- 非必要不创建 `__init__.py`；仅用于公共接口导出、必要的包解析或实际初始化逻辑，
  不为目录标记或说明文字创建。`tests/__init__.py` 保留以避免同名第三方包遮蔽样例项目。
- `beans` 负责声明和发现，`context` 负责实例化和依赖解析，避免互相循环引用。
- `beans`、`context`、`aop` 不依赖 FastAPI；Web 集成集中在 `web`，启动编排放在 `boot`。
- 容器属于应用实例，禁止使用全局可变容器保存所有应用的 Bean。
- `ContextUtil` 使用 ContextVar 绑定当前应用容器；在 lifespan 和请求中自动绑定，
  独立任务显式绑定。不以全局默认容器兜底，避免多应用串用 Bean。
- 组件默认递归扫描启动类所在包，允许显式配置范围；`*` 匹配一层，
  `**` 匹配任意层级。支持无 `__init__.py` 的目录，不遍历或导入整个环境中的包。
- 缺失依赖、重复 Bean 和无法解析的循环依赖必须提供明确异常，不静默降级。
- 属性注入必须显式声明类型及 `autowired()`，不自动注入普通属性。
  在创建实例和最终 AOP 代理后注入属性，允许引用已创建的 Bean 以解析属性循环依赖。
  纯构造器循环仍报错；构造器不得访问尚未注入的属性。
- `autowired(lazy=True)` 延迟到首次属性访问才解析依赖；组件及 `@bean(lazy=True)`
  跳过启动时的主动创建，非延迟依赖仍可提前创建它。延迟创建保留单例与 AOP。
  同步访问执行同步初始化；异步初始化使用 `await context.aget_bean(...)`，
  未创建的延迟 Bean 不执行销毁。
- Bean 声明统一支持 `name`、`scope`、`lazy`、`primary`、`qualifiers`、`depends_on`、
  `init_method`、`destroy_method`。`singleton` 按应用缓存，`prototype` 每次获取创建，
  不启动时主动创建，不缓存实例，不自动销毁；多例循环依赖明确报错。
- `primary` 仅用于多个候选时选择唯一首选；限定符先过滤候选。
  `autowired`、`inject` 及容器获取方法支持 `qualifier`。
  `depends_on` 使用 Bean 名，依赖先初始化，缺失或初始化环必须报错。
- AOP 需兼容同步与异步调用，保留函数签名及元数据。
- 切面使用 `@aspect`，通知使用 `@before`、`@after`、`@after_returning`、
  `@after_throwing`、`@around`；切点匹配方法全限定名，支持 `*`、`**` 和谓词。
  代理不得修改全局类；切面自身和生命周期方法不增强，同步目标不允许异步通知。
- 支持通过 `annotation(name)` 定义业务方法注解，方法使用 `@logged` 等注解，
  通知使用 `@before(logged)` 等声明注解切点；公共注解集中定义并复用。
- 资源初始化和销毁接入 ASGI lifespan，禁止导入模块时启动服务或创建外部连接。
- 初始化回调可使用 `@postconstruct`，只接收 self，支持同步和异步；
  在依赖注入完成后每实例调用一次，先执行注解回调，再执行显式 init_method。
  同名回调去重，继承回调按基类到子类执行，不进入 AOP 通知链。
- 框架实现不得依赖 `examples`；示例仅通过公开接口使用框架。
- `tests` 是使用框架的样例项目，不是框架单元测试目录；启动类继承
  `PythonBootApplication`，仅通过框架公开接口接入。
- 用户授权验证后，再按变更范围执行相应测试；不得擅自运行。
