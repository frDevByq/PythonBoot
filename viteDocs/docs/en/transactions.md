# Transactions

`@transactional` only supplies metadata; the application-level `TransactionInterceptor` executes it. Synchronous methods resolve `PlatformTransactionManager`, asynchronous methods resolve `AsyncPlatformTransactionManager`. `transaction_manager` selects by bean name; otherwise normal type/primary resolution applies.

```python
from pythonboot import Isolation, Propagation, transactional

class OrderService:
    @transactional(propagation=Propagation.REQUIRED, isolation=Isolation.READ_COMMITTED,
                   timeout=30, name="create-order", rollback_for=(BusinessError,),
                   no_rollback_for=(ValidationError,), transaction_manager="databaseTransactionManager")
    def create(self, command: CreateOrder) -> Order: ...
```

Parameters: `propagation=REQUIRED` (`REQUIRED`, `SUPPORTS`, `MANDATORY`, `REQUIRES_NEW`, `NOT_SUPPORTED`, `NEVER`, `NESTED`); `isolation=DEFAULT` (`READ_UNCOMMITTED`, `READ_COMMITTED`, `REPEATABLE_READ`, `SERIALIZABLE`); `timeout=-1`; `read_only=False`; `name=None`; `rollback_for=(Exception,)`; `no_rollback_for=()`; and `transaction_manager=None`.

The closest rollback rule wins; a tie goes to no-rollback. Non-`Exception` `BaseException` values always roll back. Participating inner scopes do not commit independently; rollback marks the shared transaction rollback-only and the outer commit raises `UnexpectedRollbackError`. `NESTED` requires savepoint support. Starters implement `get_transaction(definition=None)`, `commit(status)`, and `rollback(status)` on the sync or async manager contract.

```java
@Transactional(propagation = Propagation.REQUIRED, isolation = Isolation.READ_COMMITTED,
  timeout = 30, rollbackFor = BusinessError.class, transactionManager = "databaseTransactionManager")
Order create(CreateOrder command) { ... }
```
