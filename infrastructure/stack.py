"""CDK stack for COS data pipeline infrastructure."""

from aws_cdk import Stack, RemovalPolicy, aws_s3 as s3
from constructs import Construct


class CosDataStack(Stack):
    """Demo stack — creates an S3 bucket for pipeline artifacts."""

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # S3 bucket for Glue job scripts and pipeline artifacts
        s3.Bucket(
            self,
            "PipelineArtifacts",
            removal_policy=RemovalPolicy.DESTROY,
            auto_delete_objects=True,
        )
