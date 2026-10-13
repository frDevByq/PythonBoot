# Web Starter 与独立实现包

`pythonboot` 提供 IoC、Bean、AOP、配置、事务抽象和任务执行，不依赖 FastAPI 或 Uvicorn。
`pythonboot-web` 在同级 `PythonBootStarter/modules/pythonboot-web` 中实现 Web 功能；
`pythonboot-starter-web` 位于 `starters/`，聚合实现包及其依赖。各包分别发布到 PyPI。

```bash
uv add pythonboot-starter-web
```

核心接口从 `pythonboot` 导入；启动类、启动装饰器、`create_app`、Controller、
路由装饰器、`inject`、`date_time` 和 `RequestContextHolder` 从 `pythonboot_web` 导入。
旧的核心包顶层 Web 导出、`pythonboot.web` 及 `pythonboot.boot.application` 已移除。
YAML 配置键 `pythonboot.web` 和 `pythonboot.docs` 保持不变。

```python
from pythonboot import autowired, service
from pythonboot_web import PythonBootApplication, controller, get, pythonboot_application

@service
class GreetingService:
    def greeting(self) -> str:
        return "Hello"

@controller(prefix="/greeting", tags=["问候"])
class GreetingController:
    service: GreetingService = autowired()

    @get("", summary="获取问候")
    def greeting(self) -> str:
        return self.service.greeting()

@pythonboot_application(scan_packages=("myapp",))
class Application(PythonBootApplication):
    pass

app = Application().app
```

两个仓库本地开发时保持同级目录。核心仓库的 `uv sync` 使用开发组安装本地 Starter
和 Web 实现；仅需要核心能力时使用 `uv sync --no-dev`。Starter 仓库使用
`uv sync --all-packages`。UV sources 的本地路径不进入发布依赖，发布元数据使用包名和版本范围。

示例位置：核心仓库 `examples/test_application.py` 和 `examples/controller/`。
纯核心应用自行创建 `ApplicationContext`，并显式调用异步 `start()`、`close()`；
Web 应用仍由 ASGI lifespan 管理容器生命周期。
