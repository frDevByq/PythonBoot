# Web Starter and implementation package

`pythonboot` provides IoC, Beans, AOP, configuration, transaction abstractions, and task execution
without depending on FastAPI or Uvicorn. `pythonboot-web` implements Web integration in the sibling
`PythonBootStarter/modules/pythonboot-web` project. `starters/pythonboot-starter-web` aggregates
the implementation and its dependencies. Each package is published independently to PyPI.

```bash
uv add pythonboot-starter-web
```

Import core APIs from `pythonboot`. Import the application class, bootstrap decorator, `create_app`,
controllers, route decorators, `inject`, `date_time`, and `RequestContextHolder` from `pythonboot_web`.
The former core top-level Web exports, `pythonboot.web`, and `pythonboot.boot.application` were removed.
YAML keys under `pythonboot.web` and `pythonboot.docs` remain unchanged.

```python
from pythonboot import autowired, service
from pythonboot_web import PythonBootApplication, controller, get, pythonboot_application

@service
class GreetingService:
    def greeting(self) -> str:
        return "Hello"

@controller(prefix="/greeting")
class GreetingController:
    service: GreetingService = autowired()

    @get("")
    def greeting(self) -> str:
        return self.service.greeting()

@pythonboot_application(scan_packages=("myapp",))
class Application(PythonBootApplication):
    pass

app = Application().app
```

Keep both repositories in sibling directories for local development. In the core repository,
`uv sync` installs the local Starter and Web implementation through the development group;
`uv sync --no-dev` installs only core dependencies. Use `uv sync --all-packages` in the Starter
workspace. Local UV sources do not change published dependency names or version ranges.

The core repository's `examples/test_application.py` and `examples/controller/` demonstrate the split.
Core-only applications create `ApplicationContext` and explicitly await `start()` and `close()`.
Web applications continue to manage container lifecycle through ASGI lifespan.
