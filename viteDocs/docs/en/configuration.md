# Configuration and auto-configuration

`config_dir` is loaded as `application.yml`, then `application-{profile}.yml` for every `active.profile`; later values merge over earlier values. Environment variables override YAML.

```python
from pydantic_settings import BaseSettings
from pythonboot import configuration_properties

@configuration_properties("payments.stripe")
class StripeProperties(BaseSettings):
    api_key: str
    timeout: int = 10
```

`configuration_properties(prefix)` only accepts `BaseSettings` subclasses. The non-empty dotted prefix is bound from YAML and the class becomes a singleton bean if it was not already a component.

Starters publish a module or `@auto_configuration` class through the `pythonboot.autoconfigure` entry-point group. Application definitions precede auto-configuration. Configurations are sorted by `order`; `imports` explicitly supplies companion classes.

```python
@auto_configuration(order=100, imports=(CacheProperties,))
@conditional_on_property("cache.enabled", having_value=True)
class CacheAutoConfiguration:
    @bean
    @conditional_on_missing_bean(Cache)
    def cache(self, properties: CacheProperties) -> Cache: return MemoryCache(properties.size)
```

| Condition | Arguments | Rule |
| --- | --- | --- |
| `conditional_on_module` | module names | every module is discoverable |
| `conditional_on_property` | `name`, `having_value`, `match_if_missing=False` | value is truthy/non-false, or equals expected value |
| `conditional_on_bean` | types or names | every candidate is registered |
| `conditional_on_missing_bean` | types or names | backs off if any candidate is registered |

Conditions run only during assembly and never create beans. YAML also configures `pythonboot.logging` and `pythonboot.docs` (`enabled`, `provider`: `scalar`/`swagger`/`redoc`, `path`, `openapi_path`).

```java
@ConfigurationProperties(prefix = "payments.stripe")
class StripeProperties {}

@AutoConfiguration
@ConditionalOnProperty(name = "cache.enabled", havingValue = "true")
class CacheAutoConfiguration {}
```
