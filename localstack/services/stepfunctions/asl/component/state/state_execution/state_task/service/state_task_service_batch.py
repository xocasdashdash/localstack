from typing import Final, Optional

from botocore.exceptions import ClientError

from localstack.aws.api.stepfunctions import HistoryEventType, TaskFailedEventDetails
from localstack.services.stepfunctions.asl.component.common.error_name.custom_error_name import (
    CustomErrorName,
)
from localstack.services.stepfunctions.asl.component.common.error_name.failure_event import (
    FailureEvent,
)
from localstack.services.stepfunctions.asl.component.state.state_execution.state_task.service.resource import (
    ResourceRuntimePart,
)
from localstack.services.stepfunctions.asl.component.state.state_execution.state_task.service.state_task_service_callback import (
    StateTaskServiceCallback,
)
from localstack.services.stepfunctions.asl.eval.environment import Environment
from localstack.services.stepfunctions.asl.eval.event.event_detail import EventDetails
from localstack.services.stepfunctions.asl.utils.boto_client import boto_client_for
from localstack.utils.strings import camel_to_snake_case


class StateTaskServiceBatch(StateTaskServiceCallback):
    _ERROR_NAME_CLIENT: Final[str] = "TODO1"
    _ERROR_NAME_AWS: Final[str] = "TODO2"

    _SUPPORTED_API_PARAM_BINDINGS: Final[dict[str, set[str]]] = {
        "submitjob": {
            "ArrayProperties",
            "ContainerOverrides",
            "DependsOn",
            "JobDefinition",
            "JobName",
            "JobQueue",
            "Parameters",
            "RetryStrategy",
            "Timeout",
            "Tags",
        }
    }

    def _get_supported_parameters(self) -> Optional[set[str]]:
        return self._SUPPORTED_API_PARAM_BINDINGS.get(self.resource.api_action.lower())

    def _from_error(self, env: Environment, ex: Exception) -> FailureEvent:
        if isinstance(ex, ClientError):
            return FailureEvent(
                error_name=CustomErrorName(self._ERROR_NAME_CLIENT),
                event_type=HistoryEventType.TaskFailed,
                event_details=EventDetails(
                    taskFailedEventDetails=TaskFailedEventDetails(
                        error=self._ERROR_NAME_CLIENT,
                        cause=ex.response["Error"][
                            "Message"
                        ],  # TODO: update to report expected cause.
                        resource=self._get_sfn_resource(),
                        resourceType=self._get_sfn_resource_type(),
                    )
                ),
            )
        return super()._from_error(env=env, ex=ex)

    def _eval_service_task(
        self,
        env: Environment,
        resource_runtime_part: ResourceRuntimePart,
        normalised_parameters: dict,
    ):
        api_action = camel_to_snake_case(self.resource.api_action)
        sqs_client = boto_client_for(
            region=resource_runtime_part.region,
            account=resource_runtime_part.account,
            service="batch",
        )
        response = getattr(sqs_client, api_action)(**normalised_parameters)
        response.pop("ResponseMetadata", None)
        env.stack.append(response)
