"""健康检查接口。"""

from typing import Annotated

from fastapi import Body, Path, Query

from pythonboot import autowired, controller, get, post
from examples.domain.common import BaseResult
from examples.domain.health import Health, HealthCheckRequest
from examples.service.health_service import HealthService

@controller(prefix="/health", tags=["健康检查"])
class HealthController:
    health_service: HealthService = autowired()

    @get("/get", response_model=BaseResult[Health], summary="获取健康状态")
    def health(
        self,
        service_name: Annotated[
            str, Query(title="服务名称", description="需要执行健康检查的服务名称"),
        ] = "pythonboot",
        detail: Annotated[
            bool, Query(title="是否返回详细信息", description="是否请求服务的详细健康信息"),
        ] = False,
    ) -> BaseResult[Health]:
        return BaseResult.success(self.health_service.health(service_name, detail))

    @get("/{service_name}", response_model=BaseResult[Health], summary="按服务名称获取健康状态")
    def health_by_service(
        self,
        service_name: Annotated[
            str, Path(title="服务名称", description="需要执行健康检查的服务名称", min_length=1),
        ],
    ) -> BaseResult[Health]:
        return BaseResult.success(self.health_service.health(service_name))

    @post("/check", response_model=BaseResult[Health], summary="提交健康检查")
    def check(
        self,
        request: Annotated[HealthCheckRequest, Body(title="健康检查请求")],
    ) -> BaseResult[Health]:
        return BaseResult.success(self.health_service.health(request.service_name, request.detail))
