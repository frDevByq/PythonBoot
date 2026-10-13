# 事务

`@transactional` 只声明元数据，应用级 AOP 的 `TransactionInterceptor` 执行事务。同步方法选择 `PlatformTransactionManager`，异步方法选择 `AsyncPlatformTransactionManager`；可由 `transaction_manager` 指定 Bean 名，否则按类型和 `primary` 解析，缺失或歧义均报错。

```python
from pythonboot import Isolation, Propagation, transactional

class OrderService:
    @transactional(
        propagation=Propagation.REQUIRED,
        isolation=Isolation.READ_COMMITTED,
        timeout=30, read_only=False, name="create-order",
        rollback_for=(BusinessError,), no_rollback_for=(ValidationError,),
        transaction_manager="databaseTransactionManager",
    )
    def create(self, command: CreateOrder) -> Order: ...
```

| 参数 | 默认值 | 说明 |
| --- | --- | --- |
| `propagation` | `REQUIRED` | `REQUIRED`、`SUPPORTS`、`MANDATORY`、`REQUIRES_NEW`、`NOT_SUPPORTED`、`NEVER`、`NESTED` |
| `isolation` | `DEFAULT` | `DEFAULT`、`READ_UNCOMMITTED`、`READ_COMMITTED`、`REPEATABLE_READ`、`SERIALIZABLE` |
| `timeout` | `-1` | `-1` 为资源默认值；否则非负秒数 |
| `read_only` | `False` | 只读提示，管理器必须支持或明确拒绝 |
| `name` | `None` | 非空事务名 |
| `rollback_for` | `(Exception,)` | 触发回滚的异常类型集合 |
| `no_rollback_for` | `()` | 不触发回滚的异常类型集合 |
| `transaction_manager` | `None` | 管理器 Bean 名 |

更具体异常规则优先；同等匹配时 `no_rollback_for` 优先。`BaseException` 中非 `Exception` 的取消/致命异常始终回滚。加入已有事务的内层作用域不独立提交，回滚会标记共享事务 rollback-only，外层提交抛 `UnexpectedRollbackError`。`NESTED` 要求管理器实现相应的保存点能力。

Starter 应实现同步或异步管理器接口的 `get_transaction(definition=None)`、`commit(status)`、`rollback(status)`；`TransactionStatus` 提供新事务、参与事务、保存点、rollback-only 与完成状态。

## Spring Boot 对照

```java
@Transactional(propagation = Propagation.REQUIRED,
  isolation = Isolation.READ_COMMITTED, timeout = 30,
  rollbackFor = BusinessError.class, noRollbackFor = ValidationError.class,
  transactionManager = "databaseTransactionManager")
public Order create(CreateOrder command) { ... }
```
