"""Placeholder test to validate CDK synth produces a valid template."""

import aws_cdk as cdk
from aws_cdk.assertions import Template

from infrastructure.stacks.app_stack import CsvProcessorStack


def test_stack_creates_s3_bucket():
    """Verify the stack creates an S3 bucket with encryption and public access blocked."""
    app = cdk.App()
    stack = CsvProcessorStack(app, "TestStack")
    template = Template.from_stack(stack)

    # EventBridge notification is managed by a custom resource, not NotificationConfiguration.
    # Verify the bucket itself exists with security settings.
    template.has_resource_properties(
        "AWS::S3::Bucket",
        {
            "BucketEncryption": {
                "ServerSideEncryptionConfiguration": [
                    {"ServerSideEncryptionByDefault": {"SSEAlgorithm": "AES256"}}
                ]
            },
            "PublicAccessBlockConfiguration": {
                "BlockPublicAcls": True,
                "BlockPublicPolicy": True,
                "IgnorePublicAcls": True,
                "RestrictPublicBuckets": True,
            },
        },
    )


def test_stack_creates_glue_job():
    """Verify the stack creates a Glue Python Shell job."""
    app = cdk.App()
    stack = CsvProcessorStack(app, "TestStack")
    template = Template.from_stack(stack)

    template.has_resource_properties(
        "AWS::Glue::Job",
        {
            "Command": {
                "Name": "pythonshell",
                "PythonVersion": "3.9",
            },
            "GlueVersion": "3.0",
            "MaxCapacity": 0.0625,
        },
    )


def test_stack_creates_lambda_function():
    """Verify the stack creates a Lambda function with correct runtime."""
    app = cdk.App()
    stack = CsvProcessorStack(app, "TestStack")
    template = Template.from_stack(stack)

    template.has_resource_properties(
        "AWS::Lambda::Function",
        {
            "Runtime": "python3.11",
            "Timeout": 30,
            "MemorySize": 128,
        },
    )


def test_stack_creates_eventbridge_rule():
    """Verify the stack creates an EventBridge rule for S3 events."""
    app = cdk.App()
    stack = CsvProcessorStack(app, "TestStack")
    template = Template.from_stack(stack)

    template.has_resource_properties(
        "AWS::Events::Rule",
        {
            "EventPattern": {
                "source": ["aws.s3"],
                "detail-type": ["Object Created"],
            }
        },
    )
