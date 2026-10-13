"""延迟创建时间单例的演示接口。"""

from datetime import datetime
from typing import Annotated

from fastapi import Depends

from pythonboot import autowired
from pythonboot_web import controller, get, inject
from examples.config.current_time import CurrentTime, PrototypeTime
from examples.domain.common import BaseResult


@controller(prefix="/lazy", tags=["延迟加载"])
class LazyController:
    current_time: CurrentTime = autowired(lazy=True)

    @get("/time", response_model=BaseResult[dict[str, datetime]], summary="获取延迟创建单例时间")
    def time(self) -> BaseResult[dict[str, datetime]]:
        bean_time = self.current_time.created_at
        return BaseResult.success({
            "bean_time": bean_time,
            "request_time": datetime.now().astimezone(),
        })

    @get("/prototype-time", response_model=BaseResult[dict[str, datetime]], summary="获取多例时间")
    def prototype_time(
        self, current_time: Annotated[PrototypeTime, Depends(inject(PrototypeTime))],
    ) -> BaseResult[dict[str, datetime]]:
        return BaseResult.success({
            "bean_time": current_time.created_at,
            "request_time": datetime.now().astimezone(),
        })
