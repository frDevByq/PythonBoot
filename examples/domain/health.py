"""健康检查响应对象。"""

from datetime import datetime

from pydantic import BaseModel, Field


class Health(BaseModel):
    status: str = Field(title="服务状态", description="当前服务的健康状态")
    service_name: str = Field(title="服务名称", description="执行健康检查的服务名称")
    detail: bool = Field(title="是否返回详细信息", description="是否请求服务的详细健康信息")


class HealthCheckRequest(BaseModel):
    service_name: str = Field(
        min_length=1, max_length=64,
        title="服务名称", description="需要执行健康检查的服务名称",
    )
    detail: bool = Field(default=False, title="是否返回详细信息", description="是否请求服务的详细健康信息")
    checked_at: datetime | None = Field(
        default=None,
        title="检查时间",
        description="格式由 pythonboot.web.datetime_format 配置",
    )
