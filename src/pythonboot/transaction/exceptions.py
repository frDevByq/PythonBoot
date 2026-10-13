"""Resource-independent transaction exceptions."""

from pythonboot.exceptions import PythonBootError


class TransactionError(PythonBootError):
    """Base class for transaction failures."""


class NoTransactionError(TransactionError):
    """A required existing transaction is missing."""


class IllegalTransactionStateError(TransactionError):
    """Invalid transaction participation, status ownership, or completion state."""


class InvalidIsolationLevelError(TransactionError):
    """The requested isolation level cannot be applied by the resource."""


class TransactionTimedOutError(TransactionError):
    """A transaction exceeded its configured timeout."""


class NestedTransactionNotSupportedError(TransactionError):
    """The resource does not support nested transactions or savepoints."""


class UnexpectedRollbackError(TransactionError):
    """Commit was requested for a transaction already marked rollback-only."""
