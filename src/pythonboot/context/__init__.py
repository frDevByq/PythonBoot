"""IoC container, dependency resolution, scopes, and lifecycle."""

from pythonboot.context.container import ApplicationContext
from pythonboot.context.injection import autowired

__all__ = ["ApplicationContext", "autowired"]
