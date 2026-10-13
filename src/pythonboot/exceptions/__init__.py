"""Framework exceptions."""


class PythonBootError(Exception):
    """Base class for framework exceptions."""


class BeanDefinitionError(PythonBootError):
    """Invalid bean declaration."""


class DuplicateBeanError(PythonBootError):
    """Duplicate bean name or ambiguous type candidates."""


class MissingBeanError(PythonBootError):
    """No bean matches the requested dependency."""


class CircularDependencyError(PythonBootError):
    """Bean dependencies form a cycle."""


class ContainerStateError(PythonBootError):
    """The container is inactive or shutting down."""


class AopError(PythonBootError):
    """Invalid aspect declaration or incompatible advice invocation."""


class ConfigurationError(PythonBootError):
    """Invalid configuration source or property binding."""


__all__ = [
    "PythonBootError", "BeanDefinitionError", "DuplicateBeanError",
    "MissingBeanError", "CircularDependencyError", "ContainerStateError",
    "AopError", "ConfigurationError",
]
