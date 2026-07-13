---
name: circleci-pipeline
description: Set up a CircleCI CI/CD pipeline for COS data projects. Installs the reference config with OIDC auth, CDK deploy, approval gates, and pyproject.toml-based dependencies. Use when bootstrapping a new COS repo with CI/CD.
---

# Skill: CircleCI Pipeline Accelerator

Installs a production-ready CircleCI pipeline into a COS data project. The pipeline uses OIDC auth, Python CDK, and the locked 6-job workflow shape defined in `steering/circleci.md`.

## Usage

Invoke this skill when setting up CI/CD in a new COS data pipeline project.

---

## Instructions

### 1. Install the steering file

Copy the authoritative steering into the target project:

```bash
mkdir -p .kiro/steering
cp steering/circleci.md .kiro/steering/circleci.md
```

Or from the accelerator repo:

```bash
git clone --depth 1 https://github.com/intraedge-services/cos-data-accelerators.git /tmp/cos-accelerators
mkdir -p .kiro/steering
cp /tmp/cos-accelerators/steering/circleci.md .kiro/steering/circleci.md
rm -rf /tmp/cos-accelerators
```

### 2. Generate the pipeline config

Create `.circleci/config.yml` using the reference configuration from `steering/circleci.md` section 7. Copy it verbatim — it's the complete, runnable config. The pipeline shape is:

```
lint → test → build → deploy-dev → approve-prod → deploy-prod
```

### 3. Configure AWS OIDC Trust

Follow `steering/circleci.md` section 1 for the full IAM setup. Summary:

```bash
AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query 'Account' --output text)
CIRCLECI_ORG_ID="<from CircleCI → Org Settings → Overview>"
```

Create the OIDC provider and IAM roles in **both** AWS accounts (dev + prod) using the trust policy and permissions boundary documented in the steering file.

### 4. Configure CircleCI Contexts

| Context | Variables |
|---|---|
| `aws-oidc-dev` | `AWS_ROLE_ARN` (dev account role), `AWS_ACCOUNT_ID` (dev account) |
| `aws-oidc-prod` | `AWS_ROLE_ARN` (prod account role), `AWS_ACCOUNT_ID` (prod account) |

Region is hardcoded to `us-east-1` in the config (not a context variable). Each context points to a different AWS account.

### 5. Create prerequisite files

All these MUST exist before the pipeline passes:

```
pyproject.toml                        — with [project.optional-dependencies.dev]
tests/__init__.py                     — test package
tests/test_placeholder.py             — at least one passing test
infrastructure/app.py                 — CDK entry point
infrastructure/cdk.json               — CDK configuration
infrastructure/stacks/__init__.py     — stacks package
infrastructure/stacks/app_stack.py    — main stack class
infrastructure/requirements.txt       — aws-cdk-lib, constructs
.circleci/config.yml                  — the pipeline config
```

### 6. Validate and push

```bash
circleci config validate .circleci/config.yml
git add -A
git commit -S -m "feat: add CircleCI pipeline with OIDC auth and CDK deploy"
git push
```

---

## Key Rules (from steering/circleci.md)

- **OIDC only** — no static AWS credentials anywhere
- **Two environments** — dev (auto on main) + prod (manual approval)
- **pyproject.toml for app deps** — not requirements.txt (exception: `infrastructure/requirements.txt` for CDK-specific deps is required)
- **CDK in `infrastructure/`** — all CDK commands run from there
- **`sudo npm install -g aws-cdk`** — cimg/* images are non-root
- **No `--all`** on cdk synth/deploy for single-stack apps
- **No placeholders** in generated configs — values from contexts or programmatic retrieval

---

## Idempotency

Safe to run multiple times. `.circleci/config.yml` is overwritten. Contexts are external and unaffected.
