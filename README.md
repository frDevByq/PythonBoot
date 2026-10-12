# PythonBoot

基于 FastAPI、借鉴 Spring Boot 的 Python 后端框架。
计划支持 Bean 扫描、IoC 容器、依赖注入、生命周期管理和 AOP。
目前已建立项目骨架和基础应用工厂，核心功能尚未实现。

要求 Python >=3.12。依赖与开发规范见 [AGENTS.md](AGENTS.md)，
模块职责见 [架构文档](docs/architecture.md)。

项目采用 `src` 包布局，先安装项目，再启动示例：

```bash
pip install -e .
uvicorn main:app --reload
```
