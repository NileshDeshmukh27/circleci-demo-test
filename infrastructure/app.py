"""CDK app entry point for COS data platform infrastructure."""

import os

import aws_cdk as cdk

from stack import CosDataStack

app = cdk.App()

env_name = os.environ.get("CDK_ENV", "dev")

CosDataStack(
    app,
    f"CosDataPipeline-{env_name}",
    env=cdk.Environment(
        account=os.environ.get("CDK_DEFAULT_ACCOUNT", os.environ.get("AWS_ACCOUNT_ID")),
        region=os.environ.get("CDK_DEFAULT_REGION", os.environ.get("AWS_REGION", "us-west-2")),
    ),
)

app.synth()
