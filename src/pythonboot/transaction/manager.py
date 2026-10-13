"""Contracts for synchronous and asynchronous resource transaction managers."""

from abc import ABC, abstractmethod
from typing import Any

from pythonboot.transaction.definition import TransactionDefinition


class SavepointManager(ABC):
    """Optional synchronous savepoint capability for nested transactions."""

    @abstractmethod
    def create_savepoint(self) -> Any:
        """Create and return an opaque resource savepoint."""

    @abstractmethod
    def rollback_to_savepoint(self, savepoint: Any) -> None:
        """Roll back to the given savepoint without completing the transaction."""

    @abstractmethod
    def release_savepoint(self, savepoint: Any) -> None:
        """Release the given savepoint."""


class AsyncSavepointManager(ABC):
    """Optional asynchronous savepoint capability for nested transactions."""

    @abstractmethod
    async def create_savepoint(self) -> Any:
        """Create and return an opaque resource savepoint."""

    @abstractmethod
    async def rollback_to_savepoint(self, savepoint: Any) -> None:
        """Roll back to the given savepoint without completing the transaction."""

    @abstractmethod
    async def release_savepoint(self, savepoint: Any) -> None:
        """Release the given savepoint."""


class TransactionStatus(ABC):
    """Expose transaction participation, rollback-only state, and completion."""

    @property
    @abstractmethod
    def is_new_transaction(self) -> bool:
        """Whether this scope owns a newly created physical transaction."""

    @property
    @abstractmethod
    def has_transaction(self) -> bool:
        """Whether this scope participates in a physical transaction."""

    @property
    @abstractmethod
    def has_savepoint(self) -> bool:
        """Whether this scope uses a savepoint in an existing transaction."""

    @property
    @abstractmethod
    def is_rollback_only(self) -> bool:
        """Whether the underlying transaction must be rolled back."""

    @abstractmethod
    def set_rollback_only(self) -> None:
        """Mark the transaction for rollback even if the business method returns."""

    @property
    @abstractmethod
    def is_completed(self) -> bool:
        """Whether this scope has already been committed or rolled back."""


class PlatformTransactionManager(ABC):
    """Synchronous transaction manager implemented by resource-specific starters.

    Managers implement propagation and isolation, reject unsupported options,
    and validate status ownership and completion. Completion must release owned
    resources and restore suspended contexts, including on failure. Participating
    rollback marks the shared transaction rollback-only; an owner attempting to
    commit that transaction must raise UnexpectedRollbackError.
    """

    @abstractmethod
    def get_transaction(self, definition: TransactionDefinition | None = None) -> TransactionStatus:
        """Create, join, suspend, or reject a transaction according to its definition."""

    @abstractmethod
    def commit(self, status: TransactionStatus) -> None:
        """Complete a scope; only the owning scope commits the physical transaction."""

    @abstractmethod
    def rollback(self, status: TransactionStatus) -> None:
        """Roll back an owned transaction or mark a participating transaction."""


class AsyncPlatformTransactionManager(ABC):
    """Asynchronous manager with the same completion contract as the sync manager.

    Implementations must clean up resources on cancellation and prevent sharing
    a non-concurrent resource transaction across independent asyncio tasks.
    """

    @abstractmethod
    async def get_transaction(self, definition: TransactionDefinition | None = None) -> TransactionStatus:
        """Create, join, suspend, or reject a transaction according to its definition."""

    @abstractmethod
    async def commit(self, status: TransactionStatus) -> None:
        """Complete a scope; only the owning scope commits the physical transaction."""

    @abstractmethod
    async def rollback(self, status: TransactionStatus) -> None:
        """Roll back an owned transaction or mark a participating transaction."""
