"""样例项目启动类：python -m tests.test_application。"""

from pathlib import Path

from pythonboot import PythonBootApplication, pythonboot_application


@pythonboot_application
class TestApplication(PythonBootApplication):
    """样例后端的应用启动与配置。"""

    def __init__(self) -> None:
        super().__init__(title="PythonBoot Test Application")

application = TestApplication(config_dir=Path(__file__).parent / "config")
app = application.app


if __name__ == "__main__":
    application.run()
