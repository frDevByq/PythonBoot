# Application and scanning

## Startup

`PythonBootApplication` exposes `app: FastAPI` and `context: ApplicationContext`. `run(host="127.0.0.1", port=8000, log_level="info")` starts Uvicorn directly; use a Uvicorn module entry for reload or multiple workers.

```python
from pythonboot import PythonBootApplication, pythonboot_application

@pythonboot_application(scan_packages=("myapp.**",), exclude=(LegacyService,))
class Application(PythonBootApplication):
    def configure(self, app):
        pass  # native FastAPI customization

app = Application(title="My API", version="1.0.0", config_dir="config").app
```

The decorator only accepts application subclasses. Constructor `scan_packages` wins over decorator metadata. Without it, a subclass scans its own package; a script without an importable parent package must specify it.

| Pattern | Meaning |
| --- | --- |
| `myapp` | package and descendants |
| `myapp.*` | direct modules/packages only |
| `myapp.**` | package and every descendant |
| `myapp.*.service.**` | composed path expression |

Namespace directories are supported. Scanning stays inside selected paths. `exclude` excludes classes from components, controllers, advice and auto-configuration; `exclude_modules` is the module-level `create_app` option.

## `create_app`

```python
from pythonboot import create_app
app = create_app(title="Inventory API", version="1.0.0", scan_packages=("inventory",),
                 config_dir="config", auto_configure=True,
                 exclude_auto_configurations=("vendor.CacheAutoConfiguration",))
```

`title`, `version`, and remaining `**options` go to `FastAPI`. PythonBoot owns the docs and OpenAPI URLs. `auto_configure=False` disables all auto-configurations; exclusions accept entry-point names or fully-qualified configuration names.

## Spring Boot equivalent

```java
@SpringBootApplication(scanBasePackages = "myapp", exclude = LegacyAutoConfiguration.class)
class Application { public static void main(String[] args) { SpringApplication.run(Application.class, args); } }
```
