# PythonBoot / Spring Boot comparison

## Equivalent order endpoint

```python
from fastapi import Body
from pydantic import BaseModel
from typing import Annotated
from pythonboot import autowired, service, transactional
from pythonboot_web import PythonBootApplication, pythonboot_application, controller, get, post

class OrderCreate(BaseModel): sku: str
@service
class OrderService:
    @transactional(name="create-order")
    def create(self, command: OrderCreate): return {"id": 1, "sku": command.sku}
    def find(self, order_id: int): return {"id": order_id}
@controller(prefix="/orders", tags=["Orders"])
class OrderController:
    service: OrderService = autowired()
    @get("/{order_id}")
    def find(self, order_id: int): return self.service.find(order_id)
    @post("")
    def create(self, body: Annotated[OrderCreate, Body()]): return self.service.create(body)
@pythonboot_application(scan_packages=("myapp",))
class Application(PythonBootApplication): pass
app = Application(config_dir="config").app
```

```java
@SpringBootApplication
class Application {
    public static void main(String[] args) {
        SpringApplication.run(Application.class, args);
    }
}

@Service
class OrderService {
    @Transactional
    Map<String, Object> create(OrderCreate command) {
        return Map.of();
    }
}

@RestController
@RequestMapping("/orders")
class OrderController {
    @GetMapping("/{id}")
    Map<String, Object> find(@PathVariable long id) {
        return Map.of();
    }
}
```

| Spring Boot | PythonBoot |
| --- | --- |
| `@SpringBootApplication` | `@pythonboot_application` + `PythonBootApplication` |
| `@Component` / `@Service` / `@Configuration` / `@Bean` | matching lowercase decorators |
| `@Autowired` / `@Qualifier` / `@Primary` | typed constructor / `autowired()` / qualifier / `primary=True` |
| `@RestController` and mappings | `@controller` and HTTP decorators |
| `@ControllerAdvice` | `@controller_advise` |
| `@Aspect` / advice | `@aspect` / advice decorators |
| `@Transactional` | `@transactional` |
| `@ConfigurationProperties` / conditions | matching PythonBoot decorators |

FastAPI remains PythonBoot's HTTP, validation, and OpenAPI layer. Bean self-invocation does not cross the AOP proxy.
