# Routes, errors and context

```python
from datetime import datetime
from typing import Annotated
from fastapi import Body, Query
from pythonboot import autowired
from pythonboot_web import controller, get, post, date_time

@controller(prefix="/orders", tags=["Orders"], dependencies=[])
class OrderController:
    service: OrderService = autowired()

    @get("/{order_id}", summary="Get order", response_model=OrderResponse)
    async def detail(self, order_id: int, at: Annotated[datetime, date_time("%Y/%m/%d"), Query()]):
        return await self.service.find(order_id, at)

    @post("", summary="Create order")
    def create(self, command: Annotated[CreateOrder, Body()]): return self.service.create(command)
```

`controller` takes all component parameters plus `prefix=""`, `tags=None`, and arbitrary `APIRouter` options. `route(path, methods=("GET",), **add_api_route_options)` is the base route decorator; `get`, `post`, `put`, `patch`, and `delete` are shortcuts. Controller routes must be instance methods and cannot use positional-only parameters, `*args`, or `**kwargs`. Discovered native `APIRouter` objects are included automatically. Native routes can use `Depends(inject(Type, name=None, qualifier=None))`.

```python
@controller_advise
class ErrorAdvice:
    @exception_handler(OrderNotFound)
    def missing(self, request, error): return {"message": str(error)}
```

`controller_advise` takes component arguments. `exception_handler` accepts an exception class or integer status. Handlers may be sync or async.

`RequestContextHolder` exposes `get_request()`, `get_response()`, `putData(key, value)`, and `getData(key, default=None)`. The response context provides `status_code`, `set_header`, `set_cookie(key, value, **options)`, and `redirect(url, status_code=307)` before response start. `pythonboot.web.datetime_format` sets default request/JSON response formatting; `date_time(format)` overrides it through `Annotated` metadata.

```java
@RestController
@RequestMapping("/orders")
class OrderController {}

@RestControllerAdvice
class ErrorAdvice {
    @ExceptionHandler(OrderNotFound.class)
    Object missing() {
        return null;
    }
}
```
