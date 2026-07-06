---
name: circleci-pipeline
description: Set up a CircleCI CI/CD pipeline with built-in governance guardrails for AWS deployments. Use when you need a reference pipeline config with OIDC auth, security scanning, approval gates, and parameterized builds for any language/runtime.
---

# Skill: CircleCI Pipeline Accelerator

Provides a production-ready CircleCI pipeline configuration with built-in governance guardrails for AWS deployments using OIDC authentication.

## Usage

Invoke this skill to install a reference CircleCI pipeline into any project. The pipeline is parameterized — teams customize language, build commands, and deploy targets without rewriting the pipeline from scratch.

### What You Get

- Reusable CircleCI config built from orbs, commands, jobs, and workflows
- AWS OIDC authentication (no long-lived credentials)
- Mandatory security/static analysis scan step
- Manual approval gate before production deployments
- Branch and context restrictions enforcing environment separation
- Standard naming conventions for jobs and workflows

---

## Instructions

### 1. Copy the template into your project

```bash
mkdir -p .circleci
cp skills/circleci-pipeline/templates/config.yml .circleci/config.yml
```

Or if installing from the accelerator repo:

```bash
git clone --depth 1 https://github.com/intraedge-services/cos-data-accelerators.git /tmp/cos-accelerators
mkdir -p .circleci
cp /tmp/cos-accelerators/skills/circleci-pipeline/templates/config.yml .circleci/config.yml
rm -rf /tmp/cos-accelerators
```

### 2. Configure CircleCI Contexts

Create the following contexts in your CircleCI organization settings:

| Context | Purpose | Required Variables |
|---|---|---|
| `aws-oidc-dev` | Dev/sandbox AWS access | `AWS_ROLE_ARN`, `AWS_REGION` |
| `aws-oidc-staging` | Staging AWS access | `AWS_ROLE_ARN`, `AWS_REGION` |
| `aws-oidc-prod` | Production AWS access | `AWS_ROLE_ARN`, `AWS_REGION` |

Each context supplies the IAM role ARN that CircleCI assumes via OIDC. The OIDC trust relationship must already be established on the AWS side.

### 3. Customize pipeline parameters

Edit `.circleci/config.yml` and update the `parameters` section at the top:

```yaml
parameters:
  language:
    type: string
    default: "python"          # python | node | java | go | dotnet
  runtime-version:
    type: string
    default: "3.11"
  install-command:
    type: string
    default: "pip install -r requirements.txt"
  lint-command:
    type: string
    default: "flake8 src/"
  test-command:
    type: string
    default: "pytest tests/ --junitxml=test-results/results.xml"
  build-command:
    type: string
    default: "zip -r package.zip src/"
  deploy-command:
    type: string
    default: "aws lambda update-function-code --function-name my-function --zip-file fileb://package.zip"
```

### 4. Validate the config

```bash
circleci config validate .circleci/config.yml
```

### 5. Push and verify

Push your branch to trigger the pipeline. The workflow will:
1. Checkout code
2. Install and cache dependencies
3. Run linting
4. Run unit tests
5. Run security/static analysis scan
6. Build/package the artifact
7. Deploy to dev/sandbox (automatic on `main`)
8. Wait for manual approval before staging/prod

---

## Documentation

For detailed guides, see:

- [Setup Guide](docs/setup.md) — OIDC configuration, context setup, prerequisites
- [Usage Guide](docs/usage.md) — Parameter overrides, customization, multi-environment workflows
- [Architecture](docs/architecture.md) — Design decisions, governance model, security controls

## Example

See [COS Integration Guide](docs/cos-integration.md) for a concrete end-to-end config tailored to the COS data pipeline project (lint → test → build → deploy to dev/prod via OIDC).

---

## Idempotency

This skill is safe to run multiple times:
- The `.circleci/config.yml` is overwritten with the latest template on each run.
- CircleCI contexts are configured externally and are not modified by this skill.

## Cross-Platform Notes

- These instructions use Unix commands (`cp`, `mkdir`, `git`). They work on macOS and Linux.
- Windows users should use equivalent PowerShell commands or WSL.
