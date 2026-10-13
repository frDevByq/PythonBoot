"""Conditional application task executor and YAML property binding."""

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from pythonboot.beans import bean
from pythonboot.beans.conditions import conditional_on_missing_bean, conditional_on_property
from pythonboot.boot.autoconfiguration import auto_configuration
from pythonboot.config import configuration_properties
from pythonboot.task import RejectionPolicy, TaskExecutor, ThreadPoolTaskExecutor


@configuration_properties("pythonboot.task.execution")
class TaskExecutionProperties(BaseSettings):
    """Settings for the default executor; environment variables override YAML."""

    model_config = SettingsConfigDict(env_prefix="PYTHONBOOT_TASK_EXECUTION_", extra="ignore")

    core_pool_size: int = Field(default=8, ge=1)
    max_pool_size: int = Field(default=32, ge=1)
    queue_capacity: int | None = Field(default=256, ge=0)
    keep_alive_seconds: float = Field(default=60, gt=0, allow_inf_nan=False)
    thread_name_prefix: str = Field(default="pythonboot-task-", min_length=1)
    allow_core_thread_timeout: bool = False
    rejection_policy: RejectionPolicy = RejectionPolicy.ABORT
    wait_for_tasks_to_complete_on_shutdown: bool = True
    await_termination_seconds: float | None = Field(default=None, ge=0, allow_inf_nan=False)


@auto_configuration(order=1000, imports=(TaskExecutionProperties,))
@conditional_on_property("pythonboot.task.execution.enabled", having_value=True, match_if_missing=True)
class TaskExecutionAutoConfiguration:
    """Provide a default executor unless an application supplies its own."""

    @bean(name="applicationTaskExecutor", destroy_method="close")
    @conditional_on_missing_bean(TaskExecutor, "applicationTaskExecutor")
    def application_task_executor(self, properties: TaskExecutionProperties) -> ThreadPoolTaskExecutor:
        return ThreadPoolTaskExecutor(**properties.model_dump())
