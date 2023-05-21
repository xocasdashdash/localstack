import pytest

from localstack.aws.connect import ServiceLevelClientFactory
from localstack.testing.aws.util import is_aws_cloud
from localstack.testing.pytest.fixtures import StackDeployError

RESOURCE_GETATT_TARGETS = [
    "DomainName",
    "EngineVersion",
    "DomainEndpoint",
    "Id",
    "Arn",
    "DomainArn",
]


class TestAttributeAccess:
    @pytest.mark.parametrize("attribute", RESOURCE_GETATT_TARGETS)
    @pytest.mark.xfail(
        reason="Some tests are expected to fail, since they try to access invalid CFn attributes"
    )
    @pytest.mark.skipif(condition=not is_aws_cloud(), reason="Exploratory test only")
    def test_getattr(
        self,
        aws_client: ServiceLevelClientFactory,
        deploy_cfn_template,
        attribute,
        template_root,
        snapshot,
    ):
        """
        Capture the behaviour of getting all available attributes of the model
        """

        try:
            stack = deploy_cfn_template(
                template_path=template_root.joinpath(
                    "resource_providers", "opensearch", "domain.yaml"
                ),
                parameters={"AttributeName": attribute},
            )
        except StackDeployError:
            pass
        else:
            snapshot.match("stack_outputs", stack.outputs)

            # check physical resource id
            res = aws_client.cloudformation.describe_stack_resource(
                StackName=stack.stack_name, LogicalResourceId="MyResource"
            )["StackResourceDetail"]
            snapshot.match("physical_resource_id", res.get("PhysicalResourceId"))