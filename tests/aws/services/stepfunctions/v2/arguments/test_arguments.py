import json

import pytest
from localstack_snapshot.snapshots.transformer import RegexTransformer

from localstack.aws.api.lambda_ import Runtime
from localstack.testing.pytest import markers
from localstack.testing.pytest.stepfunctions.utils import (
    create_and_record_execution,
)
from localstack.utils.strings import short_uid
from tests.aws.services.stepfunctions.templates.arguments.arguments_templates import (
    ArgumentTemplates,
)
from tests.aws.services.stepfunctions.templates.services.services_templates import (
    ServicesTemplates as SerT,
)


@markers.snapshot.skip_snapshot_verify(
    paths=[
        "$..tracingConfiguration",
        "$..redriveCount",
        "$..redriveStatus",
        "$..RedriveCount",
    ]
)
class TestArgumentsBase:
    @markers.aws.validated
    @pytest.mark.parametrize(
        "template_path",
        [
            ArgumentTemplates.BASE_LAMBDA_EMPTY,
            ArgumentTemplates.BASE_LAMBDA_LITERALS,
            ArgumentTemplates.BASE_LAMBDA_EXPRESSION,
            ArgumentTemplates.BASE_LAMBDA_EMPTY_GLOBAL_QL_JSONATA,
        ],
        ids=[
            "BASE_LAMBDA_EMPTY",
            "BASE_LAMBDA_LITERALS",
            "BASE_LAMBDA_EXPRESSION",
            "BASE_LAMBDA_EMPTY_GLOBAL_QL_JSONATA",
        ],
    )
    def test_base_cases(
        self,
        sfn_snapshot,
        aws_client,
        create_iam_role_for_sfn,
        create_state_machine,
        create_lambda_function,
        template_path,
    ):
        function_name = f"lambda_func_{short_uid()}"
        create_res = create_lambda_function(
            func_name=function_name,
            handler_file=SerT.LAMBDA_ID_FUNCTION,
            runtime=Runtime.python3_12,
        )
        sfn_snapshot.add_transformer(RegexTransformer(function_name, "lambda_function_name"))
        function_arn = create_res["CreateFunctionResponse"]["FunctionArn"]
        template = ArgumentTemplates.load_sfn_template(template_path)
        template["States"]["State0"]["Resource"] = function_arn
        definition = json.dumps(template)
        exec_input = json.dumps({"input_value": "string literal", "input_values": [1, 2, 3]})
        create_and_record_execution(
            stepfunctions_client=aws_client.stepfunctions,
            create_iam_role_for_sfn=create_iam_role_for_sfn,
            create_state_machine=create_state_machine,
            sfn_snapshot=sfn_snapshot,
            definition=definition,
            execution_input=exec_input,
        )
