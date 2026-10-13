# AOP

```python
from pythonboot import annotation, around, aspect, before

logged = annotation("logged")

@aspect(order=10)
class LoggingAspect:
    @before(logged)
    def before_call(self, join_point): print(join_point.method.qualified_name)

    @around("myapp.service.**.*", order=1)
    async def measure(self, join_point): return await join_point.proceed()

class PaymentService:
    @logged
    def pay(self): ...
```

`aspect` is a managed component: it accepts all component parameters plus `order=0`. Lower orders enter the chain first. `before`, `after`, `after_returning`, `after_throwing`, and `around` accept `cut` and `order=0`.

`cut` can be a qualified method-path string, `Pointcut`, `MethodAnnotation` from `annotation(name)`, or `Callable[[MethodInfo], bool]`. In expressions, `*` matches within one path segment and `**` occupies a whole segment and matches any number of segments. `MethodInfo` exposes `bean_name`, `target_type`, `method_name`, `method`, and `qualified_name`; `ProceedingJoinPoint` adds `proceed(*args, **kwargs)`.

Async advice cannot target synchronous methods. Signatures and metadata are preserved. Aspects, lifecycle methods, and self-invocations are not advised; proxies do not mutate global classes.

```java
@Aspect @Component @Order(10) class LoggingAspect {
  @Before("@annotation(Logged)") void before(JoinPoint p) {}
  @Around("execution(* myapp.service..*(..))") Object around(ProceedingJoinPoint p) throws Throwable { return p.proceed(); }
}
```
