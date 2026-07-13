#!/usr/bin/env python3
"""CDK application entry point for the CSV Processor Pipeline."""

import aws_cdk as cdk
from stacks.app_stack import CsvProcessorStack

app = cdk.App()

CsvProcessorStack(
    app,
    "CsvProcessorStack",
    env=cdk.Environment(region="us-east-1"),
)

app.synth()
