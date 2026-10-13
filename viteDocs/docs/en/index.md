# PythonBoot

PythonBoot is a FastAPI-based backend framework with a Spring Boot-inspired programming model. It keeps FastAPI intact and adds component scanning, an application-scoped IoC container, injection, lifecycle management, AOP, transaction abstractions, task execution, and auto-configuration.

## Minimal application

```python
from pythonboot import PythonBootApplication, pythonboot_application

@pythonboot_application
class Application(PythonBootApplication):
    pass

app = Application().app
```

The application class package is scanned recursively by default. The container starts and stops in ASGI lifespan.

- Python >= 3.12; FastAPI, Pydantic, pydantic-settings, PyYAML and wrapt are runtime dependencies.
- Controllers are classes marked with `@controller`; FastAPI parameters, dependencies and response models remain native.
- Every bean belongs to an application instance. A bean cannot be obtained from an inactive container.
- `application.yml` and profile-specific YAML files supply configuration.

Continue with [Application and scanning](/en/application), or read the [PythonBoot / Spring Boot comparison](/en/spring-comparison).
