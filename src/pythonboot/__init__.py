"""PythonBoot public interfaces."""

from pythonboot.aop import (
    JoinPoint, MethodAnnotation, MethodInfo, Pointcut, ProceedingJoinPoint, annotation,
    after, after_returning, after_throwing, around, aspect, before, pointcut,
)
from pythonboot.beans import Scope, bean, component, configuration, ondestroy, postconstruct, service
from pythonboot.boot import auto_configuration
from pythonboot.beans.conditions import (
    conditional_on_bean, conditional_on_missing_bean,
    conditional_on_module, conditional_on_property,
)
from pythonboot.context import ApplicationContext, autowired
from pythonboot.config import ConfigurationPropertiesOptions, configuration_properties
from pythonboot.util import ContextUtil
from pythonboot.task import RejectionPolicy, TaskExecutor, TaskRejectedError, ThreadPoolTaskExecutor
from pythonboot.transaction import (
    AsyncPlatformTransactionManager, AsyncSavepointManager, Isolation,
    PlatformTransactionManager, Propagation, SavepointManager,
    TransactionAttribute, TransactionDefinition, TransactionInterceptor, TransactionStatus,
    get_transaction_attribute, transactional,
)

__all__ = [
    "auto_configuration", "conditional_on_bean", "conditional_on_missing_bean",
    "conditional_on_module", "conditional_on_property",
    "ApplicationContext", "bean", "component", "configuration", "service",
    "aspect", "pointcut", "before", "after", "after_returning", "after_throwing", "around",
    "JoinPoint", "ProceedingJoinPoint", "MethodInfo", "Pointcut",
    "annotation", "MethodAnnotation",
    "autowired",
    "Scope",
    "ContextUtil",
    "TaskExecutor", "ThreadPoolTaskExecutor", "TaskRejectedError", "RejectionPolicy",
    "postconstruct", "ondestroy",
    "configuration_properties", "ConfigurationPropertiesOptions",
    "Propagation", "Isolation", "TransactionDefinition", "TransactionAttribute",
    "TransactionStatus", "PlatformTransactionManager", "AsyncPlatformTransactionManager",
    "SavepointManager", "AsyncSavepointManager", "transactional", "get_transaction_attribute",
    "TransactionInterceptor",
]
