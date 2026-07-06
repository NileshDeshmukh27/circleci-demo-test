# COS Data Pipeline — Integration Guide

Step-by-step instructions to install the CircleCI Pipeline Accelerator into the
`aws-cos-data-pipeline` repository.

---

## Prerequisites

| Requirement | Status |
|---|---|
| CircleCI org with OIDC trust established | Already done |
| CircleCI contexts `aws-oidc-dev` and `aws-oidc-prod` created | Must be configured |
| `aws-cos-data-pipeline` repo connected to CircleCI | Must be connected |
| IAM roles for dev and prod with OIDC trust policy | Already done |

---

## Step 1: Copy the accelerator template

From the `aws-cos-data-pipeline` repo root:

```bash
# Clone the accelerator (private repo, requires access)
git clone --depth 1 https://github.com/intraedge-services/cos-data-accelerators.git /tmp/cos-accelerators

# Copy the template
mkdir -p .circleci
cp /tmp/cos-accelerators/skills/circleci-pipeline/templates/config.yml .circleci/config.yml

# Clean up
rm -rf /tmp/cos-accelerators
```

---

## Step 2: Configure for the COS data pipeline project

Replace the contents of `.circleci/config.yml` with this project-specific config:

```yaml
version: 2.1

orbs:
  aws-cli: circleci/aws-cli@4.1

executors:
  python:
    docker:
      - image: cimg/python:3.11
    resource_class: medium
    working_directory: ~/project

commands:
  install-deps:
    steps:
      - restore_cache:
          keys:
            - cos-deps-v1-{{ checksum "requirements.txt" }}
            - cos-deps-v1-
      - run:
          name: Install dependencies
          command: pip install -r requirements.txt
      - save_cache:
          key: cos-deps-v1-{{ checksum "requirements.txt" }}
          paths:
            - ~/.cache/pip

  assume-aws-role:
    steps:
      - aws-cli/setup:
          role_arn: ${AWS_ROLE_ARN}
          region: ${AWS_REGION}
          role_session_name: "circleci-cos-data-pipeline-${CIRCLE_BUILD_NUM}"

jobs:
  lint:
    executor: python
    steps:
      - checkout
      - install-deps
      - run:
          name: Check formatting (black)
          command: black --check src/ tests/
      - run:
          name: Lint (ruff)
          command: ruff check src/ tests/
      - run:
          name: Type check (mypy)
          command: mypy src/

  test:
    executor: python
    steps:
      - checkout
      - install-deps
      - run:
          name: Run tests
          command: pytest tests/ --junitxml=test-results/results.xml --cov=src/ --cov-report=html:coverage-report
      - store_test_results:
          path: test-results
      - store_artifacts:
          path: coverage-report
          destination: coverage

  build:
    executor: python
    steps:
      - checkout
      - install-deps
      - run:
          name: Package project
          command: |
            mkdir -p dist
            zip -r dist/package.zip src/ -x "*.pyc" -x "__pycache__/*"
      - persist_to_workspace:
          root: ~/project
          paths:
            - dist/

  deploy-dev:
    executor: python
    steps:
      - attach_workspace:
          at: ~/project
      - assume-aws-role
      - run:
          name: Deploy to dev
          command: |
            # Upload Glue job scripts
            aws s3 cp dist/package.zip s3://${GLUE_ASSETS_BUCKET}/scripts/package.zip

            # Update Step Functions state machine
            if [ -f state-machine.asl.json ]; then
              aws stepfunctions update-state-machine \
                --state-machine-arn ${STATE_MACHINE_ARN} \
                --definition file://state-machine.asl.json
            fi

  deploy-prod:
    executor: python
    steps:
      - attach_workspace:
          at: ~/project
      - assume-aws-role
      - run:
          name: Deploy to production
          command: |
            # Upload Glue job scripts
            aws s3 cp dist/package.zip s3://${GLUE_ASSETS_BUCKET}/scripts/package.zip

            # Update Step Functions state machine
            if [ -f state-machine.asl.json ]; then
              aws stepfunctions update-state-machine \
                --state-machine-arn ${STATE_MACHINE_ARN} \
                --definition file://state-machine.asl.json
            fi

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

## Step 3: Configure CircleCI contexts

Navigate to **CircleCI → Organization Settings → Contexts** and configure:

### `aws-oidc-dev`

| Variable | Value |
|---|---|
| `AWS_ROLE_ARN` | `arn:aws:iam::<DEV_ACCOUNT_ID>:role/CircleCI-COS-Data-Dev` |
| `AWS_REGION` | `us-west-2` |
| `GLUE_ASSETS_BUCKET` | `cos-data-glue-assets-dev` |
| `STATE_MACHINE_ARN` | `arn:aws:states:us-west-2:<DEV_ACCOUNT_ID>:stateMachine:cos-data-pipeline-dev` |

### `aws-oidc-prod`

| Variable | Value |
|---|---|
| `AWS_ROLE_ARN` | `arn:aws:iam::<PROD_ACCOUNT_ID>:role/CircleCI-COS-Data-Prod` |
| `AWS_REGION` | `us-west-2` |
| `GLUE_ASSETS_BUCKET` | `cos-data-glue-assets-prod` |
| `STATE_MACHINE_ARN` | `arn:aws:states:us-west-2:<PROD_ACCOUNT_ID>:stateMachine:cos-data-pipeline-prod` |

**Production context restrictions (recommended):**
- Project restriction: only `aws-cos-data-pipeline` repo
- Expression restriction: `pipeline.git.branch == "main"`

---

## Step 4: Add missing dev dependencies

The pipeline runs `black`, `ruff`, and `mypy`. Ensure they're in `requirements.txt`:

```bash
# Check if they're already present
grep -E "black|ruff|mypy" requirements.txt

# If missing, add them
echo "ruff>=0.4.0" >> requirements.txt
```

The existing `requirements.txt` already includes `black`, `flake8`, and `mypy`.
Add `ruff` as the faster replacement for `flake8` (or keep `flake8` and replace
`ruff check` with `flake8` in the lint job).

---

## Step 5: Validate locally

```bash
# Install CircleCI CLI
brew install circleci

# Validate config
circleci config validate .circleci/config.yml
```

---

## Step 6: Push and verify

```bash
# Create feature branch
git checkout -b feature/add-circleci-pipeline

# Stage and commit
git add .circleci/config.yml
git commit -m "feat: add CircleCI pipeline (OIDC auth, dev/prod deploy)"

# Push
git push -u origin feature/add-circleci-pipeline
```

The pipeline will run `lint → test → build` on the feature branch. Once merged
to `main`, it will additionally run `deploy-dev → [manual approval] → deploy-prod`.

---

## What happens on each trigger

| Trigger | Jobs that run |
|---|---|
| Push to feature branch | lint → test → build |
| Merge to `main` | lint → test → build → deploy-dev → (wait for approval) → deploy-prod |
| Manual approval clicked | deploy-prod executes |

---

## Customization points

| What to change | Where |
|---|---|
| Linting tools | `lint` job steps (swap ruff for flake8, add pylint, etc.) |
| Test command | `test` job `pytest` command |
| Deploy targets | `deploy-dev`/`deploy-prod` run steps |
| Additional Glue jobs | Add more `aws s3 cp` commands in deploy steps |
| Lambda deploys | Add `aws lambda update-function-code` in deploy steps |
| Cache invalidation | Bump `cos-deps-v1` to `cos-deps-v2` |

---

## Troubleshooting

### "Could not assume role"
- Verify the OIDC trust policy on the IAM role includes the CircleCI org ID
- Check that `AWS_ROLE_ARN` in the context points to the correct role
- Ensure the role exists in the correct account (dev vs prod)

### Lint failures on first run
- Run `black src/ tests/` locally to auto-format before pushing
- Run `ruff check --fix src/ tests/` to auto-fix lint issues

### Tests fail but pass locally
- Check Python version matches (CI uses 3.11)
- Ensure all test dependencies are in `requirements.txt`
- Verify moto mocks match the AWS service versions used
