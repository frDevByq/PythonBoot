# PythonBoot

PythonBoot is a core framework with a Spring Boot-inspired programming model. It provides component scanning, an application-scoped IoC container, injection, lifecycle management, AOP, transaction abstractions, task execution, and auto-configuration.

- Python >= 3.12; the core depends on Pydantic, pydantic-settings, PyYAML, and wrapt.
- Every bean belongs to an application instance. A bean cannot be obtained from an inactive container.
- `application.yml` and profile-specific YAML files supply configuration.

The sibling `PythonBootStarter/viteDocs` site maintains Web applications, FastAPI integration, bootstrap, and routing documentation.
