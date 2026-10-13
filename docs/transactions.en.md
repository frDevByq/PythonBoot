# Transaction API

[中文](transactions.md) | English

`pythonboot.transaction` provides database-independent, Spring-style transaction contracts. The framework includes an application-level `TransactionInterceptor` that automatically enhances transactional methods on container Beans. A database starter or application supplies a concrete transaction-manager Bean; the framework does not create database connections.

```python
from pythonboot import Isolation, Propagation, transactional


class OrderService:
    @transactional(
        propagation=Propagation.REQUIRED,
        isolation=Isolation.READ_COMMITTED,
        timeout=30,
        rollback_for=(Exception,),
        no_rollback_for=(ValueError,),
        transaction_manager="orderTransactionManager",
    )
    async def create_order(self) -> None:
        ...
```

`@transactional`, `@transactional()`, and parameterized forms are supported. The decorator only adds metadata, preserving the original signature and sync/async kind. Read the metadata with `get_transaction_attribute(method)`; `@around(transactional)` matches transactional methods. `transaction_manager` is optional and names the manager Bean resolved by the interceptor.

## AOP execution

Synchronous methods resolve `PlatformTransactionManager` by type. Asynchronous methods resolve and initialize `AsyncPlatformTransactionManager` through `aget_bean`. Without an explicit manager name, normal container type matching and primary rules apply; a named manager is also type-checked. A missing or ambiguous manager fails before the target method runs.

The interceptor surrounds ordinary business advice. It calls `get_transaction`, calls `commit` after normal completion, and on a business error calls either `rollback` or `commit` according to the rollback rules before re-raising the original error. A completion failure raises its own error while retaining the original business-error chain; completion is never attempted twice. The manager cleans up resources after completion failures. Without an explicit name, the transaction uses the method's qualified name. Cancellation also follows the rollback path, and the asynchronous manager guarantees cleanup during cancellation.

No aspect declaration or framework-package scanning is needed: apply `@transactional` directly. Enhancement exists only for calls through a container Bean proxy. Internal `self.method()` calls, direct instances, static methods, class methods, private methods, and lifecycle callbacks are not enhanced. Generators and async generators are unsupported. Concrete managers implement propagation, suspension, savepoints, and rollback-only behavior; the interceptor consistently starts and completes a transaction scope.

## Manager contract

A synchronous starter implements `PlatformTransactionManager`; an asynchronous starter implements `AsyncPlatformTransactionManager`. Both provide `get_transaction(definition)`, `commit(status)`, and `rollback(status)`, with `await` for asynchronous methods. `definition=None` means the default transaction definition; `timeout=-1` delegates to the manager's default timeout, and all other values are seconds. `read_only` is a resource optimization hint, not a guaranteed write prohibition.

`TransactionStatus` reports whether a physical transaction exists, whether it is new, whether it uses a savepoint, whether it is rollback-only, and whether it has completed. `set_rollback_only()` marks it for rollback. Savepoint support is exposed separately by `SavepointManager` or `AsyncSavepointManager`.

| Propagation | Manager behavior |
| --- | --- |
| REQUIRED | Join an existing transaction, otherwise create one. |
| SUPPORTS | Join an existing transaction, otherwise run without one. |
| MANDATORY | Require an existing transaction or fail. |
| REQUIRES_NEW | Suspend an existing transaction and create an independent one. |
| NOT_SUPPORTED | Suspend an existing transaction and run without one. |
| NEVER | Require no existing transaction or fail. |
| NESTED | Create a savepoint in an existing transaction, otherwise create one. |

Isolation levels are DEFAULT, READ_UNCOMMITTED, READ_COMMITTED, REPEATABLE_READ, and SERIALIZABLE. A concrete resource must explicitly reject unsupported propagation modes, isolation levels, or savepoint capabilities.

An inner scope that joins a transaction does not commit independently. Its rollback marks the shared transaction rollback-only; when the outer scope tries to commit, it rolls back and raises `UnexpectedRollbackError`. A failed savepoint scope rolls back to that savepoint. An independent transaction restores suspended context after completion. Managers validate manager ownership and completion state to prevent repeated commit or rollback, release owned resources and restore context on completion failure or cancellation, and prevent concurrently running independent async tasks from sharing a non-concurrent database Session.

## Rollback rules

`TransactionAttribute.rollback_on(error)` rolls back all `Exception` instances by default. Python has no Java-style checked-exception distinction. Use `rollback_for` and `no_rollback_for` to set explicit rules. The most specific matching class in the exception hierarchy wins; at equal specificity a no-rollback rule wins. If no rule matches, the transaction commits. Cancellation, system exit, and other non-`Exception` `BaseException` values always roll back.
