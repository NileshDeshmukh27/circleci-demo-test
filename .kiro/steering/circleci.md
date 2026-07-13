---
inclusion: always
---

# CircleCI Pipeline Rules — COS Data Platform

Single authoritative file for all CircleCI pipeline generation. The `.kiro/steering/circleci.md` redirect stub points here — this file is the source of truth.

---

## 1. Auth & Security (OIDC + IAM)

- **OIDC only. Never generate static AWS credentials** in any config, context, or script.
- **Use the `circleci/aws-cli` orb's `setup` command with `role_arn`.** Do not use `aws configure` or export keys.

### IAM OIDC Identity Provider (one-time per account)

> Angle-bracket placeholders are acceptable ONLY in this section (one-time manual setup). Never in generated configs.

```bash
CIRCLECI_ORG_ID="<your-circleci-org-id>"  # from CircleCI → Org Settings → Overview
AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query 'Account' --output text)
```

```json
{
  "Url": "https://oidc.circleci.com/org/<CIRCLECI_ORG_ID>",
  "ClientIdList": ["<CIRCLECI_ORG_ID>"],
  "ThumbprintList": ["9e99a48a9960b14926bb7f3b02e22da2b0ab7280"]
}
```

### IAM Role Trust Policy (per-account, per-environment role)

> Create this role in **both** AWS accounts (dev + prod). The OIDC Identity Provider must also exist in both accounts. Replace `<ACCOUNT_ID>` with the respective account ID for each.

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Federated": "arn:aws:iam::<ACCOUNT_ID>:oidc-provider/oidc.circleci.com/org/<CIRCLECI_ORG_ID>"
      },
      "Action": "sts:AssumeRoleWithWebIdentity",
      "Condition": {
        "StringEquals": {
          "oidc.circleci.com/org/<CIRCLECI_ORG_ID>:aud": "<CIRCLECI_ORG_ID>"
        },
        "StringLike": {
          "oidc.circleci.com/org/<CIRCLECI_ORG_ID>:sub": "org/<CIRCLECI_ORG_ID>/project/<PROJECT_ID>/user/*"
        }
      }
    }
  ]
}
```

### Least-Privilege Permissions Boundary (CDK Deploy Role)

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "CDKDeployPermissions",
      "Effect": "Allow",
      "Action": [
        "cloudformation:*", "s3:*", "iam:PassRole", "iam:GetRole",
        "iam:CreateRole", "iam:AttachRolePolicy", "iam:PutRolePolicy",
        "iam:DeleteRole", "iam:DeleteRolePolicy", "iam:DetachRolePolicy",
        "ssm:GetParameter", "ssm:PutParameter", "sts:AssumeRole",
        "lambda:*", "glue:*", "states:*", "events:*", "logs:*", "sns:*", "sqs:*"
      ],
      "Resource": "*"
    },
    {
      "Sid": "DenyDangerousActions",
      "Effect": "Deny",
      "Action": [
        "organizations:*", "account:*", "iam:CreateUser",
        "iam:CreateAccessKey", "iam:DeactivateMFADevice",
        "iam:DeleteAccountPasswordPolicy"
      ],
      "Resource": "*"
    }
  ]
}
```

---

## 2. Environments

- **Two environments only: `dev` and `production`.** No staging/QA/UAT.
- **Contexts: `aws-oidc-dev` and `aws-oidc-prod`.** Do not invent others.
- **Deploy to dev: automatic on `main`.** Deploy to prod: manual approval gate.
- **Separate AWS accounts** — dev and prod each have their own AWS account. OIDC provider, IAM roles, and CDK bootstrap must be configured in both accounts independently.
- **Region: `us-east-1`** in both accounts.

---

## 3. Pipeline Shape (Locked)

```
lint → test → build → deploy-dev → approve-prod → deploy-prod
```

| Job | What It Does |
|-----|-------------|
| `lint` | `black --check`, `ruff check`, `mypy` on `src/`, `tests/`, `infrastructure/` |
| `test` | `pytest tests/` — runs ALL tests (unit, integration, CDK assertions) in a single invocation with `--cov`. No marker filter — integration tests live in `tests/` alongside unit tests. |
| `build` | Build `cos_data_lib` wheel + `cdk synth --ci --quiet` from `infrastructure/`. Both persist to workspace. |
| `deploy-dev` | OIDC auth → `cdk bootstrap` → `cdk deploy` (auto on `main`) |
| `approve-prod` | Manual approval (type: approval) |
| `deploy-prod` | OIDC auth → `cdk bootstrap` → `cdk deploy` (after approval) |

- Feature branches: lint → test → build only. **No deploys.**
- Integration tests: inside `test` job (same `pytest tests/` invocation), not a separate stage.
- Wheel build: inside `build` job, not a separate publish step.

---

## 4. Tech Stack

- **Python 3.11+** on `cimg/python:3.11-node` (combined image for CDK CLI).
- **Dependencies: `pip install -e ".[dev]"` from `pyproject.toml`** (PEP 621). Never generate `requirements.txt` for application dependencies. The only `requirements.txt` allowed is `infrastructure/requirements.txt` (CDK-specific deps used by `cdk synth`).
- **CDK lives in `infrastructure/` subdirectory.** All CDK commands run from there.
- **Mocking: `moto` only.** No localstack, docker-compose, or real AWS calls in tests.

---

## 5. Generation-Time Correctness Rules

Rules that prevent real deployment failures:

### sudo for global npm installs

```yaml
# ✅ CORRECT — cimg/* images are non-root
command: sudo npm install -g aws-cdk

# ❌ WRONG — EACCES failure
command: npm install -g aws-cdk
```

### All referenced files must exist in the same commit

```
pyproject.toml
tests/__init__.py
tests/test_placeholder.py
infrastructure/app.py
infrastructure/cdk.json
infrastructure/stacks/__init__.py
infrastructure/stacks/app_stack.py
infrastructure/requirements.txt
.circleci/config.yml
```

### No --all for single-stack apps

```yaml
# ✅ Single-stack (common case)
cdk synth --ci --quiet
cdk deploy --require-approval never --ci --app cdk.out

# ❌ WRONG for single-stack
cdk synth --all --ci --quiet
```

### No placeholders in generated configs

Values come from CircleCI contexts (`${AWS_ROLE_ARN}`) or are retrieved programmatically. Never output `<YOUR_ACCOUNT_ID>` in anything executable.

### Validate before presenting as done

Run `circleci config validate .circleci/config.yml` on any generated config. Fix errors first.

---

## 6. What NOT to Add

- Slack/Teams notifications (SNS handles runtime alerting)
- SonarQube/SonarCloud (project uses ruff/black/mypy)
- Docker image builds (no containers)
- Terraform steps (IaC is CDK)
- PyPI publishing (wheel stays local)
- Scheduled/cron workflows (Step Functions triggers pipelines)
- Matrix builds (single Python 3.11)
- Great Expectations/Pandera as CI gates (DQ runs at Glue runtime)
- dbt steps (not in use)
- `cdk diff` as separate job (run locally)
- Separate CDK test/snapshot jobs (assertions run in pytest)
- Separate security scanner jobs (add to lint if needed)
- Separate integration test jobs (run in test job)
- Separate wheel build jobs (run in build job)

---

## 7. Reference Pipeline Configuration

The complete, runnable config implementing all rules above:

```yaml
version: 2.1

orbs:
  aws-cli: circleci/aws-cli@4.1
  node: circleci/node@5.2

executors:
  python-node:
    docker:
      - image: cimg/python:3.11-node
    resource_class: medium
    working_directory: ~/project

commands:
  install-python-deps:
    steps:
      - restore_cache:
          keys:
            - cos-py-deps-v1-{{ checksum "pyproject.toml" }}
            - cos-py-deps-v1-
      - run:
          name: Install Python dependencies
          command: pip install -e ".[dev]"
      - save_cache:
          key: cos-py-deps-v1-{{ checksum "pyproject.toml" }}
          paths:
            - ~/.cache/pip

  install-cdk-deps:
    steps:
      - restore_cache:
          keys:
            - cos-cdk-deps-v1-{{ checksum "infrastructure/requirements.txt" }}
            - cos-cdk-deps-v1-
      - run:
          name: Install AWS CDK CLI
          command: sudo npm install -g aws-cdk
      - run:
          name: Install CDK Python dependencies
          command: pip install -r infrastructure/requirements.txt
      - run:
          name: Install CDK Node dependencies (if present)
          command: |
            if [ -f infrastructure/package-lock.json ]; then
              cd infrastructure && npm ci
            fi
      - save_cache:
          key: cos-cdk-deps-v1-{{ checksum "infrastructure/requirements.txt" }}
          paths:
            - ~/.cache/pip
            - infrastructure/node_modules

  assume-aws-role:
    steps:
      - aws-cli/setup:
          role_arn: ${AWS_ROLE_ARN}
          region: us-east-1
          role_session_name: "circleci-cos-data-${CIRCLE_BUILD_NUM}"

  cdk-bootstrap:
    steps:
      - run:
          name: CDK bootstrap
          command: |
            cd infrastructure
            cdk bootstrap aws://${AWS_ACCOUNT_ID}/us-east-1 --ci

  cdk-deploy:
    steps:
      - run:
          name: CDK deploy
          command: |
            cd infrastructure
            cdk deploy --require-approval never --ci --app cdk.out --outputs-file cdk-outputs.json
      - store_artifacts:
          path: infrastructure/cdk-outputs.json
          destination: cdk-outputs

jobs:
  lint:
    executor: python-node
    steps:
      - checkout
      - install-python-deps
      - run:
          name: Check formatting (black)
          command: black --check src/ tests/ infrastructure/
      - run:
          name: Lint (ruff)
          command: ruff check src/ tests/ infrastructure/
      - run:
          name: Type check (mypy)
          command: mypy src/ tests/ infrastructure/

  test:
    executor: python-node
    steps:
      - checkout
      - install-python-deps
      - run:
          name: Run pytest (unit + integration + CDK assertions)
          command: |
            pytest tests/ \
              --junitxml=test-results/results.xml \
              --cov=src/ \
              --cov-report=html:coverage-report \
              --cov-report=term-missing
      - store_test_results:
          path: test-results
      - store_artifacts:
          path: coverage-report
          destination: coverage

  build:
    executor: python-node
    steps:
      - checkout
      - install-python-deps
      - install-cdk-deps
      - run:
          name: Build cos_data_lib wheel
          command: pip wheel . --no-deps -w dist/
      - run:
          name: CDK synth — validate infrastructure templates
          command: |
            cd infrastructure
            cdk synth --ci --quiet
      - persist_to_workspace:
          root: ~/project
          paths:
            - .

  deploy-dev:
    executor: python-node
    steps:
      - attach_workspace:
          at: ~/project
      - install-cdk-deps
      - assume-aws-role
      - cdk-bootstrap
      - cdk-deploy

  deploy-prod:
    executor: python-node
    steps:
      - attach_workspace:
          at: ~/project
      - install-cdk-deps
      - assume-aws-role
      - cdk-bootstrap
      - cdk-deploy

workflows:
  build-test-deploy:
    jobs:
      - lint:
          filters:
            branches:
              only: /.*/
      - test:
          requires:
            - lint
          filters:
            branches:
              only: /.*/
      - build:
          requires:
            - test
          filters:
            branches:
              only: /.*/
      - deploy-dev:
          requires:
            - build
          context:
            - aws-oidc-dev
          filters:
            branches:
              only: main
      - approve-prod:
          type: approval
          requires:
            - deploy-dev
          filters:
            branches:
              only: main
      - deploy-prod:
          requires:
            - approve-prod
          context:
            - aws-oidc-prod
          filters:
            branches:
              only: main
```

---

## 8. Prerequisite Checklist

Before presenting any pipeline as complete:

- [ ] `pyproject.toml` with `[project.optional-dependencies.dev]`
- [ ] `tests/` with at least one test file
- [ ] `infrastructure/app.py`
- [ ] `infrastructure/cdk.json`
- [ ] `infrastructure/stacks/__init__.py` + `app_stack.py`
- [ ] `infrastructure/requirements.txt` (aws-cdk-lib, constructs)
- [ ] `.circleci/config.yml`
- [ ] All Python files pass `black --check`
- [ ] Config passes `circleci config validate`
