# Setup Guide

Prerequisites and one-time configuration for the CircleCI Pipeline Accelerator.

---

## Prerequisites

| Requirement | Notes |
|---|---|
| CircleCI account | Organization-level access to create contexts |
| AWS account | Sandbox/dev environment with OIDC provider configured |
| CircleCI CLI (optional) | For local config validation: `brew install circleci` |
| GitHub/Bitbucket repo | Connected to CircleCI for pipeline triggers |

---

## 1. AWS OIDC Provider (already established)

This accelerator assumes the AWS-side OIDC trust is already in place. For reference, the trust chain looks like:

```
CircleCI Job → OIDC Token → AWS STS AssumeRoleWithWebIdentity → IAM Role → AWS Resources
```

The IAM role's trust policy should look like:

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
          "oidc.circleci.com/org/<CIRCLECI_ORG_ID>:sub": "org/<CIRCLECI_ORG_ID>/project/*/user/*"
        }
      }
    }
  ]
}
```

To restrict to specific projects, replace the `sub` wildcard:

```
"org/<CIRCLECI_ORG_ID>/project/<PROJECT_ID>/user/*"
```

---

## 2. CircleCI Contexts

Contexts inject environment-specific variables into jobs without storing secrets in the repo.

### Create contexts

Navigate to **CircleCI → Organization Settings → Contexts** and create:

| Context Name | Purpose | Variables |
|---|---|---|
| `aws-oidc-dev` | Dev/sandbox deployments | `AWS_ROLE_ARN`, `AWS_REGION` |
| `aws-oidc-staging` | Staging deployments | `AWS_ROLE_ARN`, `AWS_REGION` |
| `aws-oidc-prod` | Production deployments | `AWS_ROLE_ARN`, `AWS_REGION` |

### Context variables

| Variable | Example Value | Description |
|---|---|---|
| `AWS_ROLE_ARN` | `arn:aws:iam::123456789012:role/CircleCI-Deploy-Dev` | IAM role ARN for OIDC assumption |
| `AWS_REGION` | `us-west-2` | Target AWS region |

### Context restrictions (recommended)

For production contexts, restrict access:

1. Go to context settings → **Security**
2. Add **Project Restrictions** — only allow specific repos
3. Add **Expression Restrictions** — limit to `main` branch:
   ```
   pipeline.git.branch == "main"
   ```

---

## 3. CircleCI Project Setup

### Connect your repository

1. Go to **CircleCI → Projects**
2. Click **Set Up Project** for your repository
3. Select the branch containing `.circleci/config.yml`
4. CircleCI auto-detects the config and starts the first pipeline

### Enable OIDC

OIDC is enabled by default for all CircleCI projects within an organization that has an OIDC provider configured. No per-project toggle is needed.

### Environment variables (project-level)

These are non-secret, project-specific values set at the project level (not in contexts):

| Variable | Example | Description |
|---|---|---|
| `DEPLOY_BUCKET` | `my-app-artifacts-dev` | S3 bucket for deploy artifacts (optional) |
| `FUNCTION_NAME` | `my-lambda-function` | Lambda function name (optional) |

Set these in **Project Settings → Environment Variables**.

---

## 4. Orbs

The pipeline uses the following orbs:

| Orb | Version | Purpose |
|---|---|---|
| `circleci/aws-cli` | `4.1` | AWS CLI setup with built-in OIDC role assumption |

### Orb security settings

By default, CircleCI organizations restrict orbs to certified/partner orbs. If you need third-party orbs:

1. Go to **Organization Settings → Security**
2. Under **Orb Security Settings**, enable "Allow uncertified orbs" (if needed)

The `circleci/aws-cli` orb is a CircleCI-certified partner orb and does not require this setting.

---

## 5. Validate Configuration

Before pushing, validate locally:

```bash
# Install CircleCI CLI (if not already installed)
brew install circleci

# Validate config syntax
circleci config validate .circleci/config.yml

# Process config (expand orbs, resolve parameters)
circleci config process .circleci/config.yml
```

---

## 6. First Run Checklist

- [ ] AWS OIDC provider exists for your CircleCI org
- [ ] IAM roles created for each environment (dev, staging, prod)
- [ ] CircleCI contexts created with `AWS_ROLE_ARN` and `AWS_REGION`
- [ ] Production context has branch/project restrictions
- [ ] Repository connected to CircleCI
- [ ] `.circleci/config.yml` committed and pushed
- [ ] Pipeline parameters customized for your project
- [ ] Config validates locally with `circleci config validate`

---

## Troubleshooting

### "Could not assume role" error

- Verify the IAM role trust policy includes your CircleCI org ID
- Check that the `aud` claim matches your org ID
- Ensure the context variable `AWS_ROLE_ARN` is set correctly

### "Unauthorized" on orb usage

- Confirm the `circleci/aws-cli` orb version exists (check [CircleCI Orb Registry](https://circleci.com/developer/orbs/orb/circleci/aws-cli))
- Verify organization orb security settings allow partner orbs

### Pipeline not triggering

- Confirm the repo is connected to CircleCI
- Check that `.circleci/config.yml` is on the default branch (or the branch you're pushing)
- Look for config errors in CircleCI's **Pipelines** tab
