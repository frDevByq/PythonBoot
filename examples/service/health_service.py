"""健康检查业务。"""

from pythonboot import autowired, service
from examples.annotations.aop_annotations import logged
from examples.config.application_config import HealthSettings
from examples.domain.health import Health


@service
class HealthService:
    settings: HealthSettings = autowired()

    @logged # AOP 样例
    def health(self) -> Health:
        return Health(status=self.settings.status)
