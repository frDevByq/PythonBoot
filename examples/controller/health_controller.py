"""健康检查接口。"""

from pythonboot import autowired, controller, get
from examples.domain.health import Health
from examples.service.health_service import HealthService

@controller(prefix="/health",tags=["health"])
class HealthController:
    health_service: HealthService = autowired()

    @get("/get", response_model=Health)
    def health(self) -> Health:
        return self.health_service.health()
