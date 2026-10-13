# PythonBoot

PythonBoot 是基于 FastAPI、借鉴 Spring Boot 组织方式的后端框架。它不替换 FastAPI，而是在其上提供组件扫描、应用级 IoC 容器、依赖注入、生命周期、AOP、事务抽象、任务执行和自动配置。

## 最小应用

```python
from pythonboot_web import PythonBootApplication, pythonboot_application

@pythonboot_application
class Application(PythonBootApplication):
    pass

app = Application().app
```

启动类默认递归扫描其所在包；容器在 ASGI lifespan 中启动和关闭。应用、请求和独立任务各自绑定自己的容器，不存在全局默认容器。

## 使用边界

- Python >= 3.12；核心依赖 Pydantic、pydantic-settings、PyYAML、wrapt；Web Starter 引入 FastAPI 和 Uvicorn。
- Controller 使用类和 `@controller`；接口继续使用 FastAPI 的 `Query`、`Body`、`Depends`、响应模型等能力。
- 所有 Bean 都归属某个应用实例。容器不激活时不能获取 Bean。
- 配置目录可提供 `application.yml` 和按 profile 覆盖的 `application-{profile}.yml`。

下一步从[应用与扫描](/zh/application)开始，或查看[PythonBoot / Spring Boot 对照](/zh/spring-comparison)。

Web 应用使用 `uv add pythonboot-starter-web` 安装。模块职责和导入迁移见
[Web Starter 与独立实现包](/zh/web-starter)。
