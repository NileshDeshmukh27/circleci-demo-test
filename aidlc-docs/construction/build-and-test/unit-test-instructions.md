# Unit Test Instructions — CSV Processor Pipeline

## Run All Tests

```bash
# From project root
pytest tests/ --junitxml=test-results/results.xml --cov=src/ --cov-report=term-missing
```

## What the Tests Verify

| Test | Assertion |
|------|-----------|
| `test_stack_creates_s3_bucket` | S3 bucket with AES256 encryption and full public access block |
| `test_stack_creates_glue_job` | Glue Python Shell job (version 3.0, 0.0625 DPU) |
| `test_stack_creates_lambda_function` | Lambda function (Python 3.11, 128 MB, 30s timeout) |
| `test_stack_creates_eventbridge_rule` | EventBridge rule sourced from `aws.s3` with `Object Created` detail-type |

## Adding Tests

CDK assertion tests live in `tests/`. Import the stack and use `Template.from_stack()`:

```python
import aws_cdk as cdk
from aws_cdk.assertions import Template
from infrastructure.stacks.app_stack import CsvProcessorStack

def test_something():
    app = cdk.App()
    stack = CsvProcessorStack(app, "TestStack")
    template = Template.from_stack(stack)
    template.has_resource_properties("AWS::SomeResource", {...})
```

## Linting

```bash
black --check src/ tests/ infrastructure/
ruff check src/ tests/ infrastructure/
mypy src/ tests/ infrastructure/
```
