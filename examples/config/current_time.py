"""首次使用时记录创建时间的单例组件。"""

from datetime import datetime

from pythonboot import component, postconstruct


@component(lazy=True, primary=True)
class CurrentTime:
    created_at: datetime

    @postconstruct
    def initialize(self) -> None:
        self.created_at = datetime.now().astimezone()


@component(scope="prototype")
class PrototypeTime(CurrentTime):
    """每次从容器获取时创建新的时间组件。"""
