"""通用接口响应对象。"""

from enum import IntEnum
from typing import Generic, TypeVar

from pydantic import BaseModel, Field


ResultType = TypeVar("ResultType")


class ResponseCode(IntEnum):
    """接口响应状态码。"""

    SUCCESS = 200
    FAILURE = 500


class BaseResult(BaseModel, Generic[ResultType]):
    """统一接口响应对象。"""

    code: ResponseCode = Field(default=ResponseCode.SUCCESS, title="响应状态码", description="接口处理状态码")
    message: str = Field(default="操作成功", title="响应消息", description="接口处理结果说明")
    result: ResultType | None = Field(default=None, title="响应数据", description="接口返回的数据")

    @classmethod
    def success(cls, result: ResultType | None = None) -> "BaseResult[ResultType]":
        """创建成功响应。"""
        return cls(code=ResponseCode.SUCCESS, message="操作成功", result=result)

    @classmethod
    def failure(cls, message: str, result: ResultType | None = None) -> "BaseResult[ResultType]":
        """创建失败响应。"""
        return cls(code=ResponseCode.FAILURE, message=message, result=result)
