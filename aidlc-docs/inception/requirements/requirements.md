# Requirements — COS Data Platform (CSV Processor)

## Intent Analysis

**User Goal**: Create deployable AWS CDK (Python) infrastructure code for an event-driven CSV processing pipeline.

**Depth Assessment**: Minimal — the request is clear, self-contained, and fully specified. No ambiguity requiring clarification questions.

---

## Functional Requirements

### FR-1: S3 Bucket with EventBridge Notifications
- Single S3 bucket for both input and output data
- EventBridge notifications enabled on the bucket (required for EventBridge rules to fire on S3 events)
- Logical key prefix structure: `input/` for raw CSVs, `output/` for processed results

### FR-2: Glue Python Shell Job
- AWS Glue job of type **Python Shell** (not Spark)
- **Input**: Reads CSV file from `s3://<bucket>/input/<filename>.csv`
- **Processing**:
  1. Lowercase all column headers
  2. Add a `processed_at` column with the current UTC timestamp
- **Output**: Writes processed CSV to `s3://<bucket>/output/<filename>.csv`
- The Glue job script is deployed as part of the CDK app (uploaded to S3)

### FR-3: EventBridge Rule
- Triggers on S3 `Object Created` events in the `input/` prefix
- Filtered to `.csv` suffix
- Region: us-east-1

### FR-4: Lambda Bridge (EventBridge → Glue)
- Lambda function invoked by the EventBridge rule
- Extracts the S3 key from the event
- Starts the Glue job with the S3 key as a job argument
- Minimal runtime (Python 3.11, small memory)

---

## Non-Functional Requirements (Implicit)

| Category | Requirement |
|----------|-------------|
| Region | us-east-1 |
| IaC Tool | AWS CDK (Python) |
| Project Layout | `infrastructure/` directory per COS conventions |
| Security | Least-privilege IAM roles for Lambda and Glue |
| Naming | CDK-generated logical IDs (no hardcoded physical names) |

---

## Out of Scope (Explicitly Excluded)
- CI/CD pipeline (user stated "that comes later")
- Multi-environment deployment
- Monitoring/alerting
- Data quality validation
- Error handling beyond basic retries
