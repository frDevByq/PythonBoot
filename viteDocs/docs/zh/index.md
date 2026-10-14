# PythonBoot

PythonBoot 是借鉴 Spring Boot 组织方式的核心框架，提供组件扫描、应用级 IoC 容器、依赖注入、生命周期、AOP、事务抽象、任务执行和自动配置。

## 使用边界

- Python >= 3.12；核心依赖 Pydantic、pydantic-settings、PyYAML、wrapt。
- 所有 Bean 都归属某个应用实例。容器不激活时不能获取 Bean。
- 配置目录可提供 `application.yml` 和按 profile 覆盖的 `application-{profile}.yml`。

Web 应用、FastAPI 集成、启动类和路由文档由同级 `PythonBootStarter/viteDocs` 维护。
