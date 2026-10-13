# AOP

## 声明切面

```python
from pythonboot import annotation, around, aspect, before

logged = annotation("logged")

@aspect(order=10)
class LoggingAspect:
    @before(logged, order=0)
    def before_call(self, join_point):
        print(join_point.method.qualified_name)

    @around("myapp.service.**.*", order=1)
    async def measure(self, join_point):
        return await join_point.proceed()

class PaymentService:
    @logged
    def pay(self) -> None: ...
```

`@aspect` 是受管组件，拥有全部组件参数，额外的 `order=0` 决定切面进入通知链的次序（小者在外）。`@before`、`@after`、`@after_returning`、`@after_throwing`、`@around` 都接收 `cut` 和可选 `order=0`；相同切面内也按通知 order 排序。

## 切点

`cut` 可以是全限定方法路径字符串、`Pointcut`、由 `annotation(name)` 创建的 `MethodAnnotation`，或 `Callable[[MethodInfo], bool]` 谓词。字符串以点分段匹配：`*` 匹配一个段内任意字符，`**` 必须独占一段并匹配任意数量路径段。

```python
from pythonboot import pointcut

services = pointcut("myapp.service.**.*")
def only_queries(method):
    return method.method_name.startswith("find_")
```

`MethodInfo` 提供 `bean_name`、`target_type`、`method_name`、`method` 和 `qualified_name`。`JoinPoint` 提供目标、方法和调用参数；`ProceedingJoinPoint` 额外提供 `proceed(*args, **kwargs)`。

同步目标不能使用异步通知；同步/异步目标均保留方法签名及元数据。切面自身、初始化和销毁回调不增强。Bean 内部自调用不会经过代理。

## Spring Boot 对照

```java
@Aspect @Component @Order(10)
class LoggingAspect {
  @Before("@annotation(Logged)") void before(JoinPoint joinPoint) {}
  @Around("execution(* myapp.service..*(..))") Object around(ProceedingJoinPoint p) throws Throwable {
    return p.proceed();
  }
}
```
