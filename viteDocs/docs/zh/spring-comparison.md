# PythonBoot / Spring Boot 对照

下面是一份同一订单接口的并排对照。PythonBoot 代码可以直接作为应用结构的起点；Spring Boot 代码用于映射概念。

## PythonBoot

```python
from typing import Annotated
from fastapi import Body
from pydantic import BaseModel
from pythonboot import autowired, service, transactional
from pythonboot_web import PythonBootApplication, pythonboot_application, controller, get, post, RequestContextHolder

class OrderCreate(BaseModel):
    sku: str

@service
class OrderService:
    @transactional(name="create-order")
    def create(self, command: OrderCreate) -> dict:
        RequestContextHolder.get_response().status_code = 201
        return {"id": 1, "sku": command.sku}

    def find(self, order_id: int) -> dict:
        return {"id": order_id}

@controller(prefix="/orders", tags=["订单"])
class OrderController:
    service: OrderService = autowired()

    @get("/{order_id}", summary="查询订单")
    def find(self, order_id: int) -> dict:
        return self.service.find(order_id)

    @post("", summary="创建订单")
    def create(self, command: Annotated[OrderCreate, Body()]) -> dict:
        return self.service.create(command)

@pythonboot_application(scan_packages=("myapp",))
class Application(PythonBootApplication):
    pass

app = Application(config_dir="config").app
```

## Spring Boot

```java
@SpringBootApplication
public class Application {
    public static void main(String[] args) {
        SpringApplication.run(Application.class, args);
    }
}

record OrderCreate(String sku) {}

@Service
class OrderService {
    @Transactional(transactionManager = "transactionManager")
    Map<String, Object> create(OrderCreate command) {
        return Map.of("id", 1, "sku", command.sku());
    }

    Map<String, Object> find(long id) {
        return Map.of("id", id);
    }
}

@RestController
@RequestMapping("/orders")
class OrderController {
    private final OrderService service;

    OrderController(OrderService service) {
        this.service = service;
    }

    @GetMapping("/{id}")
    Map<String, Object> find(@PathVariable long id) {
        return service.find(id);
    }

    @PostMapping
    Map<String, Object> create(@RequestBody OrderCreate body) {
        return service.create(body);
    }
}
```

| Spring Boot | PythonBoot |
| --- | --- |
| `@SpringBootApplication` | `@pythonboot_application` + `PythonBootApplication` |
| `@Component` / `@Service` / `@Configuration` / `@Bean` | 同名小写装饰器 |
| `@Autowired` / `@Qualifier` / `@Primary` | 构造器类型注解、`autowired()` / `qualifier` / `primary=True` |
| `@RestController` / Mapping | `@controller` / `@get`、`@post` 等 |
| `@ControllerAdvice` | `@controller_advise`（保持现有 API 拼写） |
| `@Aspect` / advice | `@aspect` / `@before` 等 |
| `@Transactional` | `@transactional` |
| `@ConfigurationProperties` | `@configuration_properties` |
| `@ConditionalOn...` | `conditional_on_...` |
| `TaskExecutor` | `TaskExecutor` / `ThreadPoolTaskExecutor` |

关键差异：PythonBoot 的 HTTP 层、参数校验和 OpenAPI 均来自 FastAPI；Bean 代理不改变全局类，Bean 自调用不经 AOP 代理。
