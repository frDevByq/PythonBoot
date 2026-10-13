# 配置与自动配置

## YAML 与属性绑定

`config_dir` 指向配置目录。框架先加载 `application.yml`，再按 `active.profile` 加载 `application-{profile}.yml`；后者递归覆盖前者。环境变量优先于 YAML。

```yaml
active:
  profile: dev
pythonboot:
  docs: { enabled: true, provider: scalar, path: /docs, openapi_path: /openapi.json }
  web: { datetime_format: "%Y-%m-%d %H:%M:%S" }
```

```python
from pydantic_settings import BaseSettings
from pythonboot import configuration_properties

@configuration_properties("payments.stripe")
class StripeProperties(BaseSettings):
    api_key: str
    timeout: int = 10
```

`@configuration_properties(prefix)` 只接受 `BaseSettings` 子类，`prefix` 是非空点分路径；未标注组件时自动注册为单例 Bean。`load_configuration(config_dir)` 可单独读取配置字典。

## 自动配置与条件

第三方 Starter 在 `pythonboot.autoconfigure` entry point 发布模块或 `@auto_configuration` 类。应用组件先注册，自动配置按 `order` 升序装配；`imports` 显式列出随配置导入的类。

```python
from pythonboot import auto_configuration, bean
from pythonboot import conditional_on_missing_bean, conditional_on_property

@auto_configuration(order=100, imports=(CacheProperties,))
@conditional_on_property("cache.enabled", having_value=True, match_if_missing=False)
class CacheAutoConfiguration:
    @bean
    @conditional_on_missing_bean(Cache)
    def cache(self, properties: CacheProperties) -> Cache:
        return MemoryCache(properties.size)
```

| 条件 | 参数 | 匹配规则 |
| --- | --- | --- |
| `conditional_on_module(*modules)` | 合法模块点分名 | 所有模块可发现 |
| `conditional_on_property(name, having_value=未设置, match_if_missing=False)` | YAML 点路径 | 未设 `having_value` 时值非空且不为 `false`；否则忽略大小写比较 |
| `conditional_on_bean(*beans)` | 类型或 Bean 名 | 全部已注册 |
| `conditional_on_missing_bean(*beans)` | 类型或 Bean 名 | 任一已注册即退让 |

条件只在装配期评估，不创建 Bean。`exclude_auto_configurations` 可以排除 entry point 名或全限定名。

## 日志与 API 文档

`pythonboot.logging` 默认 INFO 和控制台格式；可设 `level`、`colors`、`loggers`，或提供含 `version` 的标准 `logging.config.dictConfig` 字典。`pythonboot.docs`：`enabled`、`provider`（`scalar` / `swagger` / `redoc`）、`path`、`openapi_path`。禁用时两个端点均不注册。

## Spring Boot 对照

```java
@ConfigurationProperties(prefix = "payments.stripe")
public class StripeProperties { private String apiKey; }

@AutoConfiguration(afterName = "...")
@ConditionalOnProperty(name = "cache.enabled", havingValue = "true")
class CacheAutoConfiguration {
  @Bean @ConditionalOnMissingBean Cache cache(CacheProperties p) { return new MemoryCache(p.getSize()); }
}
```
