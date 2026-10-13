"""样例项目启动类：python -m examples.test_application。"""

from pathlib import Path
import sys

from pythonboot_web import PythonBootApplication, pythonboot_application, RequestContextHolder


@pythonboot_application
class TestApplication(PythonBootApplication):
    """样例后端的应用启动与配置。"""

    def __init__(self, *, config_dir: str | Path | None = None) -> None:
        super().__init__(title="PythonBoot Example Application", config_dir=config_dir)


if __name__ == "__main__":
    package_root = str(Path(__file__).parent.parent)
    if package_root not in sys.path:
        sys.path.insert(0, package_root)
    TestApplication.__module__ = "examples.test_application"
    sys.modules["examples.test_application"] = sys.modules[__name__]

application = TestApplication(config_dir=Path(__file__).parent / "config")
app = application.app


if __name__ == "__main__":
    application.run()
