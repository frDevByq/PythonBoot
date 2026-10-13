"""健康检查业务。"""

from pythonboot import autowired, service
from tests.config.aop_annotations import logged
from tests.config.application_config import HealthSettings
from tests.domain.health import Health


@service
class HealthService:
    settings: HealthSettings = autowired()

    @logged
    def health(self) -> Health:
        return Health(status=self.settings.status)
