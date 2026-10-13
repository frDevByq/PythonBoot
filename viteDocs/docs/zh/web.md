# 路由、异常与上下文

## 类控制器与原生 FastAPI

```python
from datetime import datetime
from typing import Annotated
from fastapi import Body, Depends, Query
from pythonboot import autowired
from pythonboot_web import controller, get, post, inject, date_time

@controller(prefix="/orders", tags=["订单"], dependencies=[])
class OrderController:
    service: OrderService = autowired()

    @get("/{order_id}", summary="查询订单", response_model=OrderResponse)
    async def detail(self, order_id: int, at: Annotated[datetime, date_time("%Y/%m/%d"), Query()]):
        return await self.service.find(order_id, at)

    @post("", summary="创建订单")
    def create(self, command: Annotated[CreateOrder, Body()]):
        return self.service.create(command)
```

`@controller` 的 Bean 参数与 `@component` 完全相同，另有 `prefix=""`、`tags: list[str] | None` 和任意 `APIRouter` 构造参数（如 `dependencies`、`responses`、`route_class`）。方法使用 `@route(path, methods=("GET",), **FastAPI add_api_route 参数)`，`@get`、`@post`、`@put`、`@patch`、`@delete` 是 HTTP 方法快捷方式。路由必须是实例方法；不支持位置专用参数、`*args`、`**kwargs`。

扫描到的原生 `APIRouter` 会自动 `include_router`。原生路由可用 `Depends(inject(Service, name=None, qualifier=None))` 从当前应用容器取 Bean。

## 异常处理

```python
from fastapi import Request
from pythonboot_web import controller_advise, exception_handler

@controller_advise
class ErrorAdvice:
    @exception_handler(OrderNotFound)
    def missing(self, request: Request, error: OrderNotFound):
        return {"message": str(error)}

    @exception_handler(404)
    async def not_found(self, request: Request, error: Exception):
        return {"message": "not found"}
```

`@controller_advise` 接受与组件相同的 Bean 参数。`@exception_handler(exception_type)` 接受 `Exception` 子类或 HTTP 状态码整数，可在一个方法上叠加。处理方法可以同步或异步。

## 请求、响应与时间格式

`RequestContextHolder.get_request()` 取得当前 `Request`；`get_response()` 取得可变响应上下文。`putData(key, value)` / `getData(key, default=None)` 存取请求范围数据。响应上下文可设置 `status_code`（100–599）、`set_header(name, value)`、`set_cookie(key, value, **cookie_options)`、`redirect(url, status_code=307)`；响应开始后不可修改。

YAML 的 `pythonboot.web.datetime_format` 控制所有 Controller `datetime` 参数和 JSON 响应的默认格式（默认 `%Y-%m-%d %H:%M:%S`）。`date_time(format)` 可放在 `Annotated` 参数或 Pydantic 字段上覆盖格式。

## Spring Boot 对照

```java
@RestController
@RequestMapping("/orders")
@Tag(name = "订单")
class OrderController {
    @GetMapping("/{id}")
    OrderResponse detail(@PathVariable long id) {
        // ...
    }
}

@RestControllerAdvice
class ErrorAdvice {
    @ExceptionHandler(OrderNotFound.class)
    Object missing(OrderNotFound ex) {
        // ...
    }
}
```
