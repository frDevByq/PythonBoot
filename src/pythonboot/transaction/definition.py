"""Resource-independent transaction definitions and rollback rules."""

from dataclasses import dataclass
from enum import IntEnum


class Propagation(IntEnum):
    """Spring-compatible transaction propagation policies."""

    REQUIRED = 0
    SUPPORTS = 1
    MANDATORY = 2
    REQUIRES_NEW = 3
    NOT_SUPPORTED = 4
    NEVER = 5
    NESTED = 6


class Isolation(IntEnum):
    """Standard transaction isolation levels; DEFAULT uses the resource default."""

    DEFAULT = -1
    READ_UNCOMMITTED = 1
    READ_COMMITTED = 2
    REPEATABLE_READ = 4
    SERIALIZABLE = 8


@dataclass(frozen=True)
class TransactionDefinition:
    """Describe a transaction without creating or binding resource connections."""

    propagation: Propagation = Propagation.REQUIRED
    isolation: Isolation = Isolation.DEFAULT
    timeout: int = -1
    read_only: bool = False
    name: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.propagation, Propagation):
            raise TypeError("propagation must be a Propagation value")
        if not isinstance(self.isolation, Isolation):
            raise TypeError("isolation must be an Isolation value")
        if isinstance(self.timeout, bool) or not isinstance(self.timeout, int) or self.timeout < -1:
            raise ValueError("timeout must be -1 or a non-negative number of seconds")
        if not isinstance(self.read_only, bool):
            raise TypeError("read_only must be a boolean")
        if self.name is not None and (not isinstance(self.name, str) or not self.name.strip()):
            raise ValueError("name must be a non-empty string or None")


@dataclass(frozen=True)
class TransactionAttribute(TransactionDefinition):
    """Add rollback rules and an optional transaction manager bean name."""

    rollback_for: tuple[type[BaseException], ...] = (Exception,)
    no_rollback_for: tuple[type[BaseException], ...] = ()
    transaction_manager: str | None = None

    def __post_init__(self) -> None:
        super().__post_init__()
        for label in ("rollback_for", "no_rollback_for"):
            rules = getattr(self, label)
            if not isinstance(rules, (tuple, list)) or any(
                not isinstance(rule, type) or not issubclass(rule, BaseException)
                for rule in rules
            ):
                raise TypeError(f"{label} must be a sequence of exception classes")
            object.__setattr__(self, label, tuple(dict.fromkeys(rules)))
        if self.transaction_manager is not None and (
            not isinstance(self.transaction_manager, str) or not self.transaction_manager.strip()
        ):
            raise ValueError("transaction_manager must be a non-empty bean name or None")

    def rollback_on(self, error: BaseException) -> bool:
        """Use the closest exception rule; exclusions win ties; fatal errors roll back."""
        if not isinstance(error, BaseException):
            raise TypeError("error must be an exception instance")
        if not isinstance(error, Exception):
            return True
        hierarchy = type(error).__mro__
        rollback_depth = min(
            (hierarchy.index(rule) for rule in self.rollback_for if rule in hierarchy),
            default=float("inf"),
        )
        exclusion_depth = min(
            (hierarchy.index(rule) for rule in self.no_rollback_for if rule in hierarchy),
            default=float("inf"),
        )
        return rollback_depth < exclusion_depth
