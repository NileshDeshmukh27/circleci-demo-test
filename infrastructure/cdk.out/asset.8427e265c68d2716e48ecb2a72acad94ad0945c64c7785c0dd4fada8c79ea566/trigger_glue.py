"""Lambda handler: EventBridge → Glue job trigger.

Receives an S3 Object Created event from EventBridge and starts
the Glue Python Shell job with the S3 key as an argument.
"""

import json
import os

import boto3

glue = boto3.client("glue")

GLUE_JOB_NAME = os.environ["GLUE_JOB_NAME"]
BUCKET_NAME = os.environ["BUCKET_NAME"]


def handler(event: dict, context: object) -> dict:
    """Start the Glue job for the uploaded CSV file."""
    # EventBridge S3 event structure
    detail = event.get("detail", {})
    s3_key = detail.get("object", {}).get("key", "")

    if not s3_key:
        print(f"No S3 key found in event: {json.dumps(event)}")
        return {"statusCode": 400, "body": "Missing S3 key"}

    print(f"Triggering Glue job '{GLUE_JOB_NAME}' for key: {s3_key}")

    response = glue.start_job_run(
        JobName=GLUE_JOB_NAME,
        Arguments={
            "--INPUT_KEY": s3_key,
            "--BUCKET_NAME": BUCKET_NAME,
        },
    )

    job_run_id = response["JobRunId"]
    print(f"Started job run: {job_run_id}")

    return {"statusCode": 200, "body": json.dumps({"jobRunId": job_run_id})}
