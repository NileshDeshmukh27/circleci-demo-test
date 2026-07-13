"""Glue Python Shell job: lowercase headers and add processed_at column.

Expected job arguments:
    --INPUT_KEY: S3 key of the uploaded CSV (e.g. input/data.csv)
    --BUCKET_NAME: Name of the S3 bucket
"""

import csv
import io
import sys
from datetime import datetime, timezone

import boto3
from awsglue.utils import getResolvedOptions

args = getResolvedOptions(sys.argv, ["INPUT_KEY", "BUCKET_NAME"])

input_key: str = args["INPUT_KEY"]
bucket_name: str = args["BUCKET_NAME"]

# Derive output key: input/foo.csv → output/foo.csv
output_key = input_key.replace("input/", "output/", 1)

s3 = boto3.client("s3")

# Read the CSV from S3
response = s3.get_object(Bucket=bucket_name, Key=input_key)
raw_content = response["Body"].read().decode("utf-8")

reader = csv.DictReader(io.StringIO(raw_content))
original_headers = reader.fieldnames or []

# Lowercase all headers
lowered_headers = [h.lower() for h in original_headers]

# Build output rows with lowercased headers and processed_at column
output_buffer = io.StringIO()
output_headers = lowered_headers + ["processed_at"]
writer = csv.DictWriter(output_buffer, fieldnames=output_headers)
writer.writeheader()

processed_at = datetime.now(timezone.utc).isoformat()

for row in reader:
    # Re-key with lowercased headers
    new_row = {h.lower(): v for h, v in row.items()}
    new_row["processed_at"] = processed_at
    writer.writerow(new_row)

# Write processed CSV to S3
s3.put_object(
    Bucket=bucket_name,
    Key=output_key,
    Body=output_buffer.getvalue().encode("utf-8"),
    ContentType="text/csv",
)

print(f"Processed {input_key} → {output_key} ({processed_at})")
