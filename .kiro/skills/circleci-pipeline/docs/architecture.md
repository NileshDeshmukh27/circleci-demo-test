# Pipeline Architecture & Governance

Design decisions, governance model, and security controls baked into the CircleCI Pipeline Accelerator.

---

## Pipeline Flow

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        build-test-deploy workflow                        │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  ┌──────┐    ┌──────┐    ┌───────────────┐    ┌───────┐               │
│  │ lint │───▶│ test │───▶│ security-scan │───▶│ build │               │
│  └──────┘    └──────┘    └───────────────┘    └───────┘               │
│                                                    │                    │
│                                                    ▼                    │
│                                            ┌────────────┐              │
│                                            │ deploy-dev │ (auto, main) │
│                                            └────────────┘              │
│                                                    │                    │
│                                                    ▼                    │
│                                         ┌──────────────────┐           │
│                                         │  approve-prod    │ (manual)  │
│                                         └──────────────────┘           │
│                                                    │                    │
│                                                    ▼                    │
│                                         ┌────────────────────┐         │
│                                         │   deploy-prod      │         │
│                                         └────────────────────┘         │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## Design Decisions

### 1. Parameterized over templated

**Decision:** Use CircleCI pipeline parameters rather than YAML anchors or external template engines.

**Why:**
- Parameters are native to CircleCI — no preprocessing step needed
- Teams override values without understanding the pipeline internals
- CircleCI UI shows parameter values for each run, improving traceability
- No drift between template and actual config

### 2. Single workflow with gates

**Decision:** One workflow (`build-test-deploy`) with a single approval gate rather than multiple triggered workflows.

**Why:**
- Full pipeline visibility in a single view
- Approval gate provides a human checkpoint before production
- Workspace persistence carries artifacts through the entire pipeline
- Easier to reason about state and dependencies

### 3. Security scan as mandatory step

**Decision:** Security scan is always part of the pipeline but uses `|| true` to avoid blocking.

**Why:**
- Ensures every build produces a security report (stored as artifact)
- Findings are visible without breaking the build on day one
- Teams can tighten this by removing `|| true` when ready for enforcement
- Provides audit trail for compliance

### 4. OIDC over static credentials

**Decision:** AWS authentication exclusively via OIDC token exchange.

**Why:**
- No long-lived credentials to rotate or leak
- Credentials are scoped to a single job run (session-named)
- IAM conditions can restrict by branch, project, and org
- Aligns with AWS security best practices and Zero Trust principles

### 5. Contexts for environment separation

**Decision:** Separate CircleCI context per environment (dev, prod).

**Why:**
- Contexts have their own access control (project restrictions, branch restrictions)
- Same pipeline config works across environments — only the context changes
- Easy to audit which projects/branches can deploy where
- Context restrictions act as a second approval layer

---

## Governance Controls

### Branch Protection

| Control | Implementation | Effect |
|---|---|---|
| Deploy only from `main` | `filters.branches.only: main` on deploy jobs | Feature branches cannot deploy |
| Quality gates on all branches | `filters.branches.only: /.*/` on lint/test/scan | PRs get feedback before merge |

### Approval Gates

| Gate | When | Who |
|---|---|---|
| `approve-prod` | After successful dev deploy | Restricted approvers (configure in CircleCI) |

### Context Restrictions

| Context | Recommended Restrictions |
|---|---|
| `aws-oidc-dev` | Project-restricted (only specific repos) |
| `aws-oidc-prod` | Project + branch + expression restricted (`main` only) |

### Audit Trail

Every pipeline run automatically records:
- Who triggered the run (commit author, approver)
- Which branch and commit SHA
- Which context was used
- Job outputs and artifacts (test results, security reports)
- Approval timestamps and approvers

---

## Security Model

### Credential Flow

```
┌───────────────┐    OIDC Token    ┌─────────────┐    AssumeRole    ┌─────────┐
│  CircleCI Job │──────────────────▶│   AWS STS   │────────────────▶│ IAM Role│
└───────────────┘                   └─────────────┘                  └─────────┘
                                                                          │
                                                                          ▼
                                                                    Temporary
                                                                    Credentials
                                                                    (15 min TTL)
```

### Least Privilege Principles

1. **Per-environment roles** — Dev role cannot touch prod resources
2. **Session naming** — `circleci-{repo}-{build-num}` for CloudTrail traceability
3. **Short-lived tokens** — OIDC tokens expire, STS credentials have limited TTL
4. **No credential storage** — Nothing persisted between jobs

### Supply Chain Security

| Threat | Mitigation |
|---|---|
| Compromised orb | Pin orb versions (`@4.1`), use only certified orbs |
| Dependency confusion | Cache lockfiles, use `pip install -r requirements.txt` (pinned) |
| Malicious PR | Deploy only from `main`, require PR reviews |
| Context leakage | Context restrictions + branch filters |

---

## Naming Conventions

### Jobs

| Pattern | Example | Purpose |
|---|---|---|
| `lint` | `lint` | Code quality checks |
| `test` | `test` | Unit/integration tests |
| `security-scan` | `security-scan` | SAST/dependency scanning |
| `build` | `build` | Artifact creation |
| `deploy-{env}` | `deploy-dev`, `deploy-prod` | Environment deployment |
| `approve-prod` | `approve-prod` | Manual approval gate |

### Contexts

| Pattern | Example |
|---|---|
| `aws-oidc-{env}` | `aws-oidc-dev`, `aws-oidc-prod` |

### Cache Keys

| Pattern | Example |
|---|---|
| `{prefix}-{{ checksum "lockfile" }}` | `deps-v1-{{ checksum "requirements.txt" }}` |

---

## Extensibility Points

### Adding environments

1. Create a new context (`aws-oidc-{env}`)
2. Add `deploy-{env}` and `approve-{env}` jobs to the workflow
3. Wire the dependency chain

### Adding job types

1. Define the job using the existing `executor` and `commands`
2. Insert into the workflow with appropriate `requires` and `filters`
3. Follow naming conventions

### Custom orbs

Teams can add orbs for specific needs:

```yaml
orbs:
  aws-cli: circleci/aws-cli@4.1
  slack: circleci/slack@4.12      # notifications
  sonarcloud: sonarsource/sonarcloud@2.0  # code quality
```

---

## Comparison with GitHub Actions Approach

| Aspect | CircleCI (this accelerator) | GitHub Actions (existing) |
|---|---|---|
| Auth model | OIDC via `aws-cli` orb | OIDC via `aws-actions/configure-aws-credentials` |
| Reusability | Orbs + commands | Reusable workflows + composite actions |
| Approval gates | Native `type: approval` jobs | Environment protection rules |
| Secrets injection | Contexts (org-level) | Environment secrets (repo-level) |
| Parameterization | Pipeline parameters | Workflow inputs |
| Caching | Built-in `save_cache`/`restore_cache` | `actions/cache` |

The governance model is equivalent — both enforce quality gates, environment separation, and manual approval before production.
