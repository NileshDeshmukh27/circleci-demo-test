# Build Instructions — CSV Processor Pipeline

## Prerequisites

- Python 3.11+
- Node.js 18+ (for CDK CLI)
- AWS CDK CLI: `sudo npm install -g aws-cdk`
- AWS credentials configured (for deploy only)

## Install Dependencies

```bash
# From project root
pip install -e ".[dev]"
pip install -r infrastructure/requirements.txt
```

## Synthesize CloudFormation Template

```bash
cd infrastructure
cdk synth --ci --quiet
```

This produces `infrastructure/cdk.out/CsvProcessorStack.template.json`.

## Deploy (requires AWS credentials + bootstrap)

```bash
cd infrastructure
cdk bootstrap aws://ACCOUNT_ID/us-east-1 --ci
cdk deploy --require-approval never --ci
```

## Project Structure

```
.
├── pyproject.toml                    # Project metadata + dev deps
├── infrastructure/
│   ├── app.py                        # CDK app entry point
│   ├── cdk.json                      # CDK toolkit config
│   ├── requirements.txt              # CDK-specific deps
│   ├── stacks/
│   │   ├── __init__.py
│   │   └── app_stack.py              # CsvProcessorStack
│   └── lambda/
│       └── trigger_glue.py           # Lambda bridge handler
├── src/
│   ├── cos_data_lib/
│   │   └── __init__.py               # Shared library (placeholder)
│   └── glue_scripts/
│       └── process_csv.py            # Glue Python Shell script
└── tests/
    ├── __init__.py
    └── test_placeholder.py           # CDK assertion tests
```
