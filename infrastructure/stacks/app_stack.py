"""CsvProcessorStack — S3 bucket, Glue job, EventBridge rule, Lambda bridge."""

import os

from aws_cdk import (
    Duration,
    RemovalPolicy,
    Stack,
)
from aws_cdk import (
    aws_events as events,
)
from aws_cdk import (
    aws_events_targets as targets,
)
from aws_cdk import (
    aws_glue as glue,
)
from aws_cdk import (
    aws_iam as iam,
)
from aws_cdk import (
    aws_lambda as _lambda,
)
from aws_cdk import (
    aws_s3 as s3,
)
from aws_cdk import (
    aws_s3_assets as s3_assets,
)
from constructs import Construct


class CsvProcessorStack(Stack):
    """Stack for the event-driven CSV processing pipeline."""

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # ─── S3 Bucket (EventBridge notifications enabled) ───────────────────
        bucket = s3.Bucket(
            self,
            "DataBucket",
            event_bridge_enabled=True,
            removal_policy=RemovalPolicy.DESTROY,
            auto_delete_objects=True,
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
            encryption=s3.BucketEncryption.S3_MANAGED,
            enforce_ssl=True,
        )

        # ─── Glue Script Asset ───────────────────────────────────────────────
        glue_script_asset = s3_assets.Asset(
            self,
            "GlueScriptAsset",
            path=os.path.join(
                os.path.dirname(__file__), "..", "..", "src", "glue_scripts", "process_csv.py"
            ),
        )

        # ─── Glue IAM Role ───────────────────────────────────────────────────
        glue_role = iam.Role(
            self,
            "GlueJobRole",
            assumed_by=iam.ServicePrincipal("glue.amazonaws.com"),
            managed_policies=[
                iam.ManagedPolicy.from_aws_managed_policy_name("service-role/AWSGlueServiceRole"),
            ],
        )

        # Grant Glue read on input/ and write on output/
        bucket.grant_read(glue_role, "input/*")
        bucket.grant_put(glue_role, "output/*")
        # Grant Glue read on the script asset
        glue_script_asset.grant_read(glue_role)

        # ─── Glue Python Shell Job ───────────────────────────────────────────
        glue_job = glue.CfnJob(
            self,
            "ProcessCsvJob",
            name=None,  # CDK generates logical name
            role=glue_role.role_arn,
            command=glue.CfnJob.JobCommandProperty(
                name="pythonshell",
                python_version="3.9",
                script_location=glue_script_asset.s3_object_url,
            ),
            glue_version="3.0",
            max_capacity=0.0625,  # Minimum for Python Shell (1/16 DPU)
            default_arguments={
                "--job-language": "python",
                "--TempDir": f"s3://{bucket.bucket_name}/tmp/",
            },
        )

        # ─── Lambda Bridge Function ──────────────────────────────────────────
        trigger_fn = _lambda.Function(
            self,
            "TriggerGlueFunction",
            runtime=_lambda.Runtime.PYTHON_3_11,
            handler="trigger_glue.handler",
            code=_lambda.Code.from_asset(os.path.join(os.path.dirname(__file__), "..", "lambda")),
            timeout=Duration.seconds(30),
            memory_size=128,
            environment={
                "GLUE_JOB_NAME": glue_job.ref,
                "BUCKET_NAME": bucket.bucket_name,
            },
        )

        # Grant Lambda permission to start the Glue job
        trigger_fn.add_to_role_policy(
            iam.PolicyStatement(
                actions=["glue:StartJobRun"],
                resources=[
                    self.format_arn(
                        service="glue",
                        resource="job",
                        resource_name=glue_job.ref,
                    )
                ],
            )
        )

        # ─── EventBridge Rule ────────────────────────────────────────────────
        events.Rule(
            self,
            "CsvUploadRule",
            event_pattern=events.EventPattern(
                source=["aws.s3"],
                detail_type=["Object Created"],
                detail={
                    "bucket": {"name": [bucket.bucket_name]},
                    "object": {"key": [{"prefix": "input/"}, {"suffix": ".csv"}]},
                },
            ),
            targets=[targets.LambdaFunction(trigger_fn)],
        )
