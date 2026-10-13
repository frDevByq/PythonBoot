"""业务服务日志切面。"""

import logging

from pythonboot import JoinPoint, after_throwing, aspect, before
from examples.annotations.aop_annotations import logged

logger = logging.getLogger(__name__)


@aspect
class LoggingAspect:
    @before(logged)
    def log_call(self, join_point: JoinPoint) -> None:
        logger.info("调用 %s", join_point.qualified_name)

    @after_throwing(logged)
    def log_error(self, join_point: JoinPoint, error: BaseException) -> None:
        logger.error("调用失败 %s：%s", join_point.qualified_name, error)
