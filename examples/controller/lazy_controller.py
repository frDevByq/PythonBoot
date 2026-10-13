"""延迟创建时间单例的演示接口。"""

from datetime import datetime
from typing import Annotated

from fastapi import Depends

from pythonboot import autowired, controller, get, inject
from examples.config.current_time import CurrentTime, PrototypeTime


@controller(prefix="/lazy", tags=["lazy"])
class LazyController:
    current_time: CurrentTime = autowired(lazy=True)

    @get("/time")
    def time(self) -> dict[str, datetime]:
        bean_time = self.current_time.created_at
        return {
            "bean_time": bean_time,
            "request_time": datetime.now().astimezone(),
        }

    @get("/prototype-time")
    def prototype_time(
        self, current_time: Annotated[PrototypeTime, Depends(inject(PrototypeTime))],
    ) -> dict[str, datetime]:
        return {
            "bean_time": current_time.created_at,
            "request_time": datetime.now().astimezone(),
        }
