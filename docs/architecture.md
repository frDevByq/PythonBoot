# 架构

PythonBoot 以 FastAPI 为 Web 底座，核心模块与 Web 适配层分离。

预期启动流程：加载配置 → 扫描 Bean 声明 → 注册元数据 →
解析依赖并创建实例 → 应用 AOP 代理 → 接入 FastAPI 路由及 lifespan。

- `beans`：发现组件，生成 Bean 定义。
- `context`：管理 Bean 实例、依赖关系、作用域和销毁流程。
- `aop`：对匹配的 Bean 方法应用通知和代理。
- `config`：读取配置并绑定属性。
- `web`：将容器能力接入 FastAPI。
- `boot`：编排上述模块，提供应用创建入口。

当前仅提供基础应用工厂及目录骨架，核心功能将逐步实现。
