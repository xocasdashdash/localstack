import json

from localstack.testing.pytest import markers
from localstack.testing.snapshots.transformer import RegexTransformer
from localstack.utils.strings import short_uid
from tests.aws.services.stepfunctions.templates.services.services_templates import (
    ServicesTemplates as ST,
)
from tests.aws.services.stepfunctions.utils import create_and_record_execution


@markers.snapshot.skip_snapshot_verify(paths=["$..loggingConfiguration", "$..tracingConfiguration"])
class TestTaskBatch:
    @staticmethod
    def _create_batch_job(aws_client, job_definition_name):
        container_props = {
            "image": "busybox",
            "vcpus": 1,
            "memory": 512,
            "command": ["sleep", "1"],
        }
        job_definition_resp = aws_client.batch.register_job_definition(
            jobDefinitionName=job_definition_name,
            type="container",
            containerProperties=container_props,
        )

        return job_definition_resp
        # job_definition_arn = job_definition_resp["jobDefinitionArn"]
        # aws_client.batch.deregister_job_definition(job_definition=job_definition_arn)

    @staticmethod
    def _create_batch_queue(aws_client, job_queue_name):
        role_name = f"r-{short_uid()}"
        create_role_resp = aws_client.iam.create_role(
            RoleName=role_name,
            AssumeRolePolicyDocument=json.dumps(
                {
                    "Version": "2012-10-17",
                    "Statement": [
                        {
                            "Effect": "Allow",
                            "Principal": {
                                "Service": [
                                    "batch.amazonaws.com",
                                    "logs.amazonaws.com",
                                    "ecs.amazonaws.com",
                                ]
                            },
                            "Action": "sts:AssumeRole",
                        },
                    ],
                }
            ),
        )
        role_arn = create_role_resp["Role"]["Arn"]

        import time

        time.sleep(60)

        env_name = f"env-{short_uid()}"
        create_env_resp = aws_client.batch.create_compute_environment(
            computeEnvironmentName=env_name, type="UNMANAGED", serviceRole=role_arn, state="ENABLED"
        )
        env_arn = create_env_resp["computeEnvironmentArn"]

        time.sleep(60)

        job_queue_definition = aws_client.batch.create_job_queue(
            jobQueueName=job_queue_name,
            state="ENABLED",
            priority=1,
            computeEnvironmentOrder=[{"order": 0, "computeEnvironment": env_arn}],
        )

        return job_queue_definition

        # job_queue_arn = job_queue_definition["jobQueueArn"]
        # aws_client.batch_client.delete_job_queue(jobQueue=job_queue_arn)
        #
        # aws_client.iam_client.delete_role(RoleName=role_name)

    @markers.aws.validated
    def test_submit_job_base(
        self,
        aws_client,
        create_iam_role_for_sfn,
        create_state_machine,
        sfn_snapshot,
    ):
        job_name = f"job-{short_uid()}"
        sfn_snapshot.add_transformer(RegexTransformer(job_name, "job_name"))
        job_queue_name = f"queue-{short_uid()}"
        sfn_snapshot.add_transformer(RegexTransformer(job_queue_name, "job_queue_name"))

        self._create_batch_job(aws_client, job_name)
        self._create_batch_queue(aws_client, job_queue_name)

        template = ST.load_sfn_template(ST.BATCH_SUBMIT_JOB_BASE)
        definition = json.dumps(template)

        exec_input = json.dumps(
            {"JobDefinition": job_name, "JobName": job_name, "JobQueue": job_queue_name}
        )
        create_and_record_execution(
            aws_client.stepfunctions,
            create_iam_role_for_sfn,
            create_state_machine,
            sfn_snapshot,
            definition,
            exec_input,
        )
