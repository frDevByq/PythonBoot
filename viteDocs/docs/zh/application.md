# 应用与扫描

## 启动方式

`PythonBootApplication` 构造后提供 `app: FastAPI` 和 `context: ApplicationContext`。`run(host="127.0.0.1", port=8000, log_level="info")` 仅适合直接启动；热重载、多 worker 请用 Uvicorn 模块入口。

```python
from pythonboot_web import PythonBootApplication, pythonboot_application

@pythonboot_application(scan_packages=("myapp.**",), exclude=(LegacyService,))
class Application(PythonBootApplication):
    def configure(self, app):
        # 可注册 FastAPI 原生中间件、路由和异常处理器
        pass

application = Application(title="My API", version="1.0.0", config_dir="config")
app = application.app
```

`@pythonboot_application` 只可修饰 `PythonBootApplication` 子类。`scan_packages` 优先级低于构造参数；类未指定且不是基类时，使用启动类所在包。独立脚本没有可导入父包时必须显式提供扫描范围。

## 扫描规则

| 表达式 | 含义 |
| --- | --- |
| `myapp` | 递归扫描包及子包 |
| `myapp.*` | 仅匹配下一层包或模块 |
| `myapp.**` | 匹配该包及任意深度子包、模块 |
| `myapp.*.service.**` | 组合路径匹配 |

扫描支持没有 `__init__.py` 的目录，仅遍历表达式覆盖的路径，不会导入整个 Python 环境。`exclude` 以类为单位，同时排除组件、控制器、异常建议和自动配置候选；`exclude_modules` 是 `create_app` 的模块级排除参数。

## `create_app`

当不需要启动类时直接创建独立 FastAPI 应用：

```python
from pythonboot_web import create_app

app = create_app(
    title="Inventory API", version="1.0.0",
    scan_packages=("inventory",), config_dir="config",
    auto_configure=True,
    exclude_auto_configurations=("vendor.CacheAutoConfiguration",),
    docs_url="/unused-by-pythonboot",
)
```

`title`、`version` 与剩余 `**options` 传给 `FastAPI`；框架接管 `docs_url`、`redoc_url` 与 `openapi_url`，使用 YAML 的文档设置。`auto_configure=False` 禁用所有自动配置。`exclude_auto_configurations` 接受入口名或自动配置的全限定名。

## Spring Boot 对照

```java
@SpringBootApplication(scanBasePackages = "myapp", exclude = LegacyAutoConfiguration.class)
public class Application {
  public static void main(String[] args) {
    SpringApplication.run(Application.class, args);
  }
}
```

PythonBoot 的 `@pythonboot_application` + `PythonBootApplication` 对应 `@SpringBootApplication`；但其运行时 Web 容器始终是 FastAPI/ASGI。
