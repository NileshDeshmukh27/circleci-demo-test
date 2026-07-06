# Usage Guide

How to customize and extend the CircleCI Pipeline Accelerator for your project.

---

## Parameter Reference

All parameters are defined at the top of `config.yml` and can be overridden without modifying the pipeline structure.

### Core Parameters

| Parameter | Type | Default | Description |
|---|---|---|---|
| `language` | string | `python` | Runtime: python, node, java, go, dotnet |
| `runtime-version` | string | `3.11` | Language version for the Docker image |
| `install-command` | string | `pip install -r requirements.txt` | Dependency installation |
| `lint-command` | string | `flake8 src/` | Linting/code style check |
| `test-command` | string | `pytest tests/ --junitxml=test-results/results.xml` | Unit test execution |
| `build-command` | string | `zip -r package.zip src/` | Build/package step |
| `scan-command` | string | `pip install bandit && bandit -r src/ ...` | Security/static analysis |

### Deployment Parameters

| Parameter | Type | Default | Description |
|---|---|---|---|
| `deploy-command-dev` | string | `echo '...'` | Deploy to dev/sandbox |
| `deploy-command-staging` | string | `echo '...'` | Deploy to staging |
| `deploy-command-prod` | string | `echo '...'` | Deploy to production |

### Infrastructure Parameters

| Parameter | Type | Default | Description |
|---|---|---|---|
| `cache-key-prefix` | string | `deps-v1` | Cache key prefix (bump to invalidate) |
| `working-directory` | string | `.` | Subdirectory for monorepo support |
| `resource-class` | string | `medium` | Job resource class |

---

## Language-Specific Examples

### Python (default)

```yaml
parameters:
  language:
    default: "python"
  runtime-version:
    default: "3.11"
  install-command:
    default: "pip install -r requirements.txt"
  lint-command:
    default: "flake8 src/ && mypy src/"
  test-command:
    default: "pytest tests/ --junitxml=test-results/results.xml --cov=src/"
  scan-command:
    default: "pip install bandit safety && bandit -r src/ -f json -o scan-results/bandit.json || true && safety check --json > scan-results/safety.json || true"
```

### Node.js

```yaml
parameters:
  language:
    default: "node"
  runtime-version:
    default: "20.11"
  install-command:
    default: "npm ci"
  lint-command:
    default: "npm run lint"
  test-command:
    default: "npm test -- --reporters=default --reporters=jest-junit"
  build-command:
    default: "npm run build && zip -r package.zip dist/"
  scan-command:
    default: "npx audit-ci --moderate || true"
  cache-key-prefix:
    default: "node-deps-v1"
```

**Note:** For Node.js, update the executor image. Replace `cimg/python` with `cimg/node` in the executors section:

```yaml
executors:
  default:
    docker:
      - image: cimg/node:<< pipeline.parameters.runtime-version >>
```

### Java (Gradle)

```yaml
parameters:
  language:
    default: "java"
  runtime-version:
    default: "17"
  install-command:
    default: "./gradlew dependencies"
  lint-command:
    default: "./gradlew checkstyleMain"
  test-command:
    default: "./gradlew test"
  build-command:
    default: "./gradlew shadowJar"
  scan-command:
    default: "./gradlew dependencyCheckAnalyze || true"
```

**Note:** Use `cimg/openjdk:<< pipeline.parameters.runtime-version >>` as the executor image.

---

## Customizing the Workflow

### Skip security scan (not recommended)

Remove the `security-scan` job from the workflow's `requires` on `build`:

```yaml
- build:
    requires:
      - test
      # - security-scan  # removed
```

### Add integration tests

Add a new job after `build`:

```yaml
jobs:
  integration-test:
    executor: default
    steps:
      - checkout-and-attach
      - install-dependencies
      - assume-aws-role
      - run:
          name: Run integration tests
          command: pytest tests/integration/ --junitxml=test-results/integration.xml
      - store_test_results:
          path: test-results

workflows:
  build-test-deploy:
    jobs:
      # ... existing jobs ...
      - integration-test:
          requires:
            - build
          context:
            - aws-oidc-dev
          filters:
            branches:
              only: main
      - deploy-dev:
          requires:
            - integration-test  # now depends on integration tests
          context:
            - aws-oidc-dev
```

### Feature branch deployments

To deploy feature branches to ephemeral environments:

```yaml
- deploy-feature:
    requires:
      - build
    context:
      - aws-oidc-dev
    filters:
      branches:
        ignore: main
```

### Scheduled pipeline (nightly builds)

Add a scheduled trigger in CircleCI project settings or use:

```yaml
workflows:
  nightly:
    triggers:
      - schedule:
          cron: "0 2 * * *"  # 2 AM UTC daily
          filters:
            branches:
              only: main
    jobs:
      - lint
      - test:
          requires:
            - lint
      - security-scan:
          requires:
            - lint
```

---

## Monorepo Support

For projects in a monorepo, set the `working-directory` parameter:

```yaml
parameters:
  working-directory:
    default: "services/my-service"
```

The executor's working directory will be set to `~/project/services/my-service`.

Update the cache key to use the correct lockfile path:

```yaml
- restore_cache:
    keys:
      - deps-v1-{{ checksum "services/my-service/requirements.txt" }}
```

---

## Caching Strategies

### Invalidate cache

Bump the `cache-key-prefix` parameter:

```yaml
parameters:
  cache-key-prefix:
    default: "deps-v2"  # was deps-v1
```

### Multiple cache paths

Extend the `install-dependencies` command's `save_cache` step:

```yaml
- save_cache:
    key: << pipeline.parameters.cache-key-prefix >>-{{ checksum "requirements.txt" }}
    paths:
      - ~/.cache/pip
      - ./venv
      - ./node_modules  # if using Node.js
```

---

## Resource Optimization

| Use Case | Resource Class | Monthly Credits (approx) |
|---|---|---|
| Lightweight linting | `small` | Low |
| Standard builds | `medium` (default) | Moderate |
| Large test suites | `large` | Higher |
| Compilation-heavy | `xlarge` | Highest |

Override per-job if needed by modifying the executor in specific jobs rather than using the parameter globally.

---

## Secrets Management

| Secret Type | Where to Store | Why |
|---|---|---|
| AWS Role ARN | CircleCI Context | Environment-specific, shared across projects |
| API keys | CircleCI Context | Rotatable, access-controlled |
| Non-secret config | Project Environment Variables | Project-specific, non-sensitive |
| Build-time constants | Pipeline Parameters | Visible in config, no sensitivity |

Never store secrets in:
- Pipeline parameters (visible in config file)
- Repository code
- Docker images
