## CircleCI Pipeline Rules — COS Data Platform

Rules governing how the AI agent generates or modifies CircleCI pipeline
configuration for COS data pipeline projects. Every rule includes a
justification comment so reviewers can trace it back to a real decision.

---

### Handoff Boundary — CircleCI vs. CDK Responsibilities

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    CircleCI (Pipeline Orchestration)                     │
│                                                                         │
│  Owns: job ordering, branch gates, approval gates, caching,            │
│        OIDC role assumption, test reporting, artifact storage            │
│                                                                         │
│  ┌──────┐  ┌──────┐  ┌───────────────────┐  ┌──────────┐  ┌────────┐ │
│  │ lint │→ │ test │→ │ build (cdk synth) │→ │deploy-dev│→ │  ...   │ │
│  └──────┘  └──────┘  └───────────────────┘  └──────────┘  └────────┘ │
│                                                    │                    │
├────────────────────────────────────────────────────┼────────────────────┤
│                    AWS CDK (Infrastructure)         │                    │
│                                                    ▼                    │
│  Owns: stack definitions, resource provisioning, IAM policies,          │
│        CloudFormation template generation, stack dependencies            │
│                                                                         │
│  CircleCI calls: cdk bootstrap → cdk deploy --all                       │
│  CDK handles:    CloudFormation create/update, resource lifecycle        │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

- **CircleCI decides WHEN and WHETHER to deploy** (branch filters, approval gates).
  **CDK decides WHAT to deploy** (stack definitions, resources, configurations).
  <!-- WHY: Clean separation means the client team can modify infrastructure (CDK
       stacks) without touching pipeline orchestration, and vice versa. Neither
       system needs to understand the other's internals. -->

- **The handoff point is the `cdk deploy` command.** CircleCI handles everything
  before it (auth, validation, gating). CDK handles everything after it
  (CloudFormation operations, resource provisioning, rollback on failure).
  <!-- WHY: This is the cleanest integration boundary. CircleCI doesn't need to
       know about individual AWS resources. CDK doesn't need to know about
       pipeline workflow logic. -->

- **If CDK deploy fails, CDK automatically rolls back the CloudFormation stack.
  CircleCI marks the job as failed. No manual cleanup needed.**
  <!-- WHY: CloudFormation's built-in rollback handles infra failures. CircleCI
       captures the failure status. The team investigates via CloudFormation
       events, not CircleCI logs. -->

---

### Access & Security Setup (OIDC + IAM)

#### IAM OIDC Identity Provider (one-time per account)

```json
{
  "Url": "https://oidc.circleci.com/org/<CIRCLECI_ORG_ID>",
  "ClientIdList": ["<CIRCLECI_ORG_ID>"],
  "ThumbprintList": ["9e99a48a9960b14926bb7f3b02e22da2b0ab7280"]
}
```
<!-- WHY: This establishes trust between the AWS account and CircleCI's OIDC
     provider. Created once per AWS account, not per project. -->

#### IAM Role Trust Policy (per-environment role)

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Federated": "arn:aws:iam::<ACCOUNT_ID>:oidc-provider/oidc.circleci.com/org/<ORG_ID>"
      },
      "Action": "sts:AssumeRoleWithWebIdentity",
      "Condition": {
        "StringEquals": {
          "oidc.circleci.com/org/<ORG_ID>:aud": "<ORG_ID>"
        },
        "StringLike": {
          "oidc.circleci.com/org/<ORG_ID>:sub": "org/<ORG_ID>/project/<PROJECT_ID>/user/*"
        }
      }
    }
  ]
}
```
<!-- WHY: The trust policy restricts which CircleCI org and project can assume
     the role. The `sub` claim pins it to a specific project — other projects
     in the same org cannot assume this role. -->

#### Least-Privilege Permissions Boundary (CDK Deploy Role)

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "CDKDeployPermissions",
      "Effect": "Allow",
      "Action": [
        "cloudformation:*",
        "s3:*",
        "iam:PassRole",
        "iam:GetRole",
        "iam:CreateRole",
        "iam:AttachRolePolicy",
        "iam:PutRolePolicy",
        "iam:DeleteRole",
        "iam:DeleteRolePolicy",
        "iam:DetachRolePolicy",
        "ssm:GetParameter",
        "ssm:PutParameter",
        "sts:AssumeRole",
        "lambda:*",
        "glue:*",
        "states:*",
        "events:*",
        "logs:*",
        "sns:*",
        "sqs:*"
      ],
      "Resource": "*"
    },
    {
      "Sid": "DenyDangerousActions",
      "Effect": "Deny",
      "Action": [
        "organizations:*",
        "account:*",
        "iam:CreateUser",
        "iam:CreateAccessKey",
        "iam:DeactivateMFADevice",
        "iam:DeleteAccountPasswordPolicy"
      ],
      "Resource": "*"
    }
  ]
}
```
<!-- WHY: The CDK deploy role needs broad permissions to create/update resources
     defined in stacks (Glue, Step Functions, Lambda, S3, IAM roles for those
     services). The Deny statement blocks destructive account-level actions that
     CDK should never perform. This is a permissions boundary — attach it to the
     role to cap maximum permissions regardless of what policies are added. -->

- **Never create IAM users or static access keys from the pipeline.**
  <!-- WHY: The pipeline authenticates via OIDC. Creating IAM users or keys from
       CI would be a privilege escalation path and defeats the OIDC model. -->

- **The CDK bootstrap role (created by `cdk bootstrap`) is separate from the
  CircleCI OIDC role. CDK's CloudFormation execution role handles actual
  resource creation — CircleCI's role just needs permission to invoke CDK.**
  <!-- WHY: CDK bootstrap creates its own execution roles with scoped permissions.
       The CircleCI OIDC role assumes CDK's roles via sts:AssumeRole. This
       layered model means CircleCI never directly creates AWS resources. -->

---

### Auth Model

- **OIDC only. Never generate static AWS credentials (access keys, secret keys) in
  any CircleCI config, context variable list, or environment variable suggestion.**
  <!-- WHY: COS uses OIDC trust between CircleCI and AWS. IAM roles are assumed
       via STS AssumeRoleWithWebIdentity. The .env.example shows AWS_PROFILE for
       local dev but CI MUST use OIDC — no long-lived credentials in pipelines. -->

- **Use the `circleci/aws-cli` orb's `setup` command with `role_arn` for AWS auth.
  Do not use `aws configure` or export `AWS_ACCESS_KEY_ID`/`AWS_SECRET_ACCESS_KEY`.**
  <!-- WHY: The aws-cli orb handles OIDC token exchange natively. Manual credential
       export bypasses the established trust chain and creates rotation burden. -->

- **AWS role ARNs and region MUST come from CircleCI contexts, not hardcoded in config.**
  <!-- WHY: Contexts are org-level with access restrictions. Hardcoding ARNs leaks
       account structure and prevents per-environment isolation. -->

- **CDK commands (`cdk deploy`, `cdk bootstrap`) inherit credentials from the OIDC
  role assumption. Do not pass `--profile`, `--access-key`, or any credential flags
  to CDK CLI commands.**
  <!-- WHY: After aws-cli/setup assumes the role via OIDC, the environment has valid
       temporary credentials. CDK picks these up automatically from the environment.
       Explicit credential flags break the OIDC chain. -->

---

### Environments

- **Only two environments exist: `dev` and `production`. Do not generate staging,
  QA, UAT, or any other environment references.**
  <!-- WHY: COS data platform operates in two AWS accounts. The .env.example
       confirms ENVIRONMENT=development. Production is the only other tier.
       Adding phantom environments creates confusion and unactionable steps. -->

- **CircleCI contexts are named `aws-oidc-dev` and `aws-oidc-prod`.
  Do not invent additional context names.**
  <!-- WHY: These match the actual contexts configured in the CircleCI org.
       Referencing non-existent contexts causes job failures at runtime. -->

- **Deploy to `dev` is automatic on the `main` branch.
  Deploy to `production` requires a manual approval gate.**
  <!-- WHY: Dev is the sandbox for validating pipeline changes. Production holds
       live data flows (Step Functions orchestrating Glue ETL) processing City of
       Scottsdale data and requires human sign-off before promotion. -->

- **CDK deploys use `--require-approval never` for dev (automated) and
  `--require-approval never` for prod (the CircleCI approval gate is the human
  check, not CDK's built-in prompt).**
  <!-- WHY: The manual approval happens at the CircleCI workflow level (approve-prod
       job). CDK's interactive approval prompt would hang in CI — it must be
       suppressed. The governance gate is CircleCI's approval job, not CDK's. -->

---

### Pipeline Shape

- **The workflow MUST follow: lint → test → build → deploy-dev → approve-prod → deploy-prod.**
  <!-- WHY: This matches the team's agreed CI/CD model from testing-guidelines.md:
       "Run linting and type checks, execute unit tests on every commit" followed
       by promotion through environments with a human gate before production. -->

- **Feature branches run lint → test → build only. Deploy jobs NEVER run on
  feature branches — only on `main`.**
  <!-- WHY: Feature branches are for PR feedback. Deployments happen only after
       merge to main. This prevents accidental infra changes from feature branches. -->

- **The `lint` job runs `black --check`, `ruff check` (or `flake8`), and `mypy`.
  These tools are in requirements.txt and the testing-guidelines steering explicitly
  lists them for CI.**
  <!-- WHY: The project's testing-guidelines.md says "Run linting (ruff, black --check)
       and type checks (mypy)" in CI/CD. These are installed dependencies, not
       aspirational additions. -->

- **The `test` job runs `pytest`. Include `--cov` for coverage reporting.**
  <!-- WHY: pytest, pytest-cov, and pytest-mock are in requirements.txt.
       The testing-guidelines say "Execute unit tests on every commit." -->

- **The `build` job packages Python code AND synthesizes the CDK app (`cdk synth`).
  CDK synth validates the infrastructure template without deploying anything.**
  <!-- WHY: cdk synth catches template errors early (missing properties, circular
       dependencies, invalid constructs) without touching AWS. It's a build-time
       check that belongs alongside Python packaging. -->

- **Do not add jobs beyond lint, test, build, deploy-dev, approve-prod, deploy-prod
  unless the user explicitly requests them. Specifically, do not add: separate
  security scanner jobs, integration test jobs, performance test jobs, Docker
  build steps, data quality validation jobs, `cdk diff` as a separate job, or
  notification jobs.**
  <!-- WHY: While Great Expectations and Pandera exist in the project, they run as
       part of the pipeline runtime (Step Functions), not as CI gate jobs. CDK diff
       is informational and can be run locally — it's not a gate. The team will
       explicitly ask for additional CI stages as needed. -->

---

### Technology Stack — Python

- **Runtime is Python 3.11+. Use `cimg/python:3.11` Docker images.**
  <!-- WHY: The project's requirements.txt and all steering files reference Python.
       The data platform uses PySpark (Glue), pandas, polars — all Python. -->

- **Dependency installation uses `pip install -r requirements.txt` by default.**
  <!-- WHY: requirements.txt exists at the repo root. This is the current state. -->

- **Migration option: `pyproject.toml` with `pip install -e ".[dev]"`.
  If the project adopts pyproject.toml, replace the install command and update the
  cache checksum key to `{{ checksum "pyproject.toml" }}`. Do NOT silently switch
  — only use pyproject.toml if the file actually exists in the repo.**
  <!-- WHY: pyproject.toml is the modern standard (PEP 621) and unifies metadata,
       dependencies, and tool config. The team may migrate to consolidate
       requirements.txt + setup.cfg + tool configs. But until pyproject.toml
       exists in the repo, use requirements.txt. This is documented as an option,
       not a default. -->

- **The project uses `moto` for mocking AWS services in tests. Do not add
  localstack, docker-compose, or real AWS calls in the test job.**
  <!-- WHY: requirements.txt does not include localstack. The testing-guidelines
       say "Use moto to mock AWS services (S3, Glue, Lambda, DynamoDB, SQS, SNS)"
       and "Mock AWS services instead of hitting real endpoints." -->

---

### Technology Stack — AWS CDK

- **CDK is written in Python (not TypeScript). The CDK app lives alongside the
  data pipeline code in the same repo.**
  <!-- WHY: The team uses Python for everything — data pipelines and infrastructure.
       Keeping CDK in Python avoids a language split and lets the same developers
       maintain both. -->

- **CDK requires Node.js as a runtime dependency (the CDK CLI is an npm package).
  Install Node.js 20 LTS and CDK CLI in the pipeline before any CDK commands.**
  <!-- WHY: Even Python CDK apps need the Node.js-based CDK CLI for synth/deploy.
       Node 20 is the current LTS. Install via: `npm install -g aws-cdk`. -->

- **CDK bootstrap (`cdk bootstrap`) must run before the first deploy to a new
  account/region. Include it as a step in deploy jobs with idempotent execution
  (it's safe to re-run — it no-ops if already bootstrapped).**
  <!-- WHY: CDK bootstrap creates the CDKToolkit stack (S3 bucket, ECR repo, IAM
       roles) needed for deployments. Running it every time is safe and ensures
       the target account is always ready. -->

- **CDK deploy command: `cdk deploy --all --require-approval never --ci`.**
  <!-- WHY: `--all` deploys all stacks in the app. `--require-approval never`
       suppresses interactive prompts (CI has no TTY). `--ci` sets non-interactive
       mode for CI environments. -->

- **CDK context values for environment selection come from environment variables
  set by the CircleCI context (e.g., `CDK_ENV=dev` or `CDK_ENV=prod`).
  Do not hardcode environment in `cdk.json` or pass `-c env=dev` in the config file.**
  <!-- WHY: Environment selection must come from the CircleCI context to maintain
       the same config file across environments. Hardcoding defeats the purpose
       of context-based separation. -->

- **NPM dependencies for CDK (if any `package.json` exists in the infra directory)
  are installed with `npm ci`. Cache `node_modules` with a checksum on
  `package-lock.json`.**
  <!-- WHY: npm ci is deterministic (uses lockfile exactly). Caching node_modules
       avoids re-downloading CDK and its dependencies on every build. -->

---

### Branch & Workflow Rules

- **Deploy jobs run only on the `main` branch. Feature branches run lint + test + build only.**
  <!-- WHY: The project uses trunk-based development. Changes merge to main via
       PR, then promote through dev → prod. No feature branch deploys. -->

- **Do not generate tag-based or release-branch triggers.**
  <!-- WHY: No release branches, version tags, or release workflow exist. The
       project uses main as the single integration branch. -->

- **Manual approval (`type: approval`) is required before `deploy-prod`.
  Do not make production deployment automatic under any condition.**
  <!-- WHY: Production runs live data pipelines processing City of Scottsdale
       data. Unattended production deploys are not acceptable. -->

---

### What NOT to Add

- Do not add Slack/Teams notification jobs (not configured for this project)
- Do not add SonarQube/SonarCloud steps (not in use — project uses flake8/ruff/mypy)
- Do not add Docker image builds (no containers in this project)
- Do not add Terraform plan/apply steps (IaC is CDK, not Terraform)
- Do not add artifact publishing to PyPI or other registries (not a library)
- Do not add scheduled/cron workflows (data pipelines are triggered by Step Functions)
- Do not add matrix builds (single Python 3.11 target)
- Do not add Great Expectations or Pandera as CI gate jobs (they run at pipeline
  runtime inside Glue/Step Functions, not as build-time checks)
- Do not add dbt steps (dbt is listed as optional in requirements, not in use)
- Do not add `cdk diff` as a separate pipeline job (run it locally before PRs)
- Do not add separate CDK test/snapshot jobs (CDK assertions run as part of pytest)
<!-- WHY for all above: None of these tools or patterns are configured in the
     current project. Adding them creates unjustified complexity, misleads
     developers about what the project uses, and bloats pipeline execution time. -->

---

### Naming Conventions

- **Job names: `lint`, `test`, `build`, `deploy-dev`, `approve-prod`, `deploy-prod`.**
  <!-- WHY: Short, predictable names matching the two-environment model.
       Consistent across all COS data repos that adopt this accelerator. -->

- **Context names: `aws-oidc-dev`, `aws-oidc-prod`.**
  <!-- WHY: Pattern matches what's configured in CircleCI org settings. -->

- **Cache key prefixes:**
  - Python: `cos-py-deps-v1-{{ checksum "requirements.txt" }}`
  - Node/CDK: `cos-node-deps-v1-{{ checksum "infrastructure/package-lock.json" }}`
  <!-- WHY: Separate prefixes for Python and Node caches. Checksums ensure
       invalidation when dependencies change. `cos-` prefix avoids org collisions. -->
