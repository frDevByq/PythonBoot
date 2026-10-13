"""健康检查响应对象。"""

from pydantic import BaseModel


class Health(BaseModel):
    status: str
