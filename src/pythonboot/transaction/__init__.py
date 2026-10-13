"""Public resource-independent transaction contracts and declarations."""

from pythonboot.transaction.decorators import get_transaction_attribute, transactional
from pythonboot.transaction.definition import Isolation, Propagation, TransactionAttribute, TransactionDefinition
from pythonboot.transaction.exceptions import (
    IllegalTransactionStateError, InvalidIsolationLevelError,
    NestedTransactionNotSupportedError, NoTransactionError,
    TransactionError, TransactionTimedOutError, UnexpectedRollbackError,
)
from pythonboot.transaction.manager import (
    AsyncPlatformTransactionManager, AsyncSavepointManager,
    PlatformTransactionManager, SavepointManager, TransactionStatus,
)
from pythonboot.transaction.interceptor import TransactionInterceptor

__all__ = [
    "Propagation", "Isolation", "TransactionDefinition", "TransactionAttribute",
    "TransactionStatus", "PlatformTransactionManager", "AsyncPlatformTransactionManager",
    "SavepointManager", "AsyncSavepointManager", "transactional", "get_transaction_attribute",
    "TransactionError", "NoTransactionError", "IllegalTransactionStateError",
    "InvalidIsolationLevelError", "TransactionTimedOutError",
    "NestedTransactionNotSupportedError", "UnexpectedRollbackError",
    "TransactionInterceptor",
]
