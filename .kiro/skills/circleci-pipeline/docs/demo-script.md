# Live Demo Script — CircleCI Pipeline (Client-Facing)

Step-by-step walkthrough for presenting to the COS external team.
Target duration: 8-10 minutes.

---

## Pre-Demo Setup Checklist

- [ ] CircleCI-connected repo with the sample `config.yml` committed
- [ ] `aws-oidc-dev` context configured with `AWS_ROLE_ARN`, `AWS_REGION`, `AWS_ACCOUNT_ID`
- [ ] At least one successful pipeline run completed (so you can show real artifacts)
- [ ] CircleCI UI open in browser (workflow graph visible)
- [ ] Editor open with `steering/circleci.md` and `steering/circleci-sample-config.yml`
- [ ] This script on a second screen or printed

---

## Demo Flow

### Part 1: The Pipeline (3 minutes)

**Open CircleCI UI → show the workflow graph:**

> "Here's the full pipeline running end-to-end. Let me walk you through each stage."

Point to each job in the graph:

| Job | What to say |
|---|---|
| `lint` | "Checks code formatting and type safety — black, ruff, mypy. Runs on every push, including feature branches." |
| `test` | "Runs pytest with coverage. Results appear in CircleCI's test tab — click here — you can see pass/fail per test." |
| `build` | "Two things happen: Python code is packaged, AND `cdk synth` validates the infrastructure templates. If your CDK has errors, it fails here — before any deployment." |
| `deploy-dev` | "Automatic on main. No human step needed. Deploys to your dev AWS account using CDK." |
| `approve-prod` | "**This is the gate.** Nothing goes to production until someone clicks approve. You can see who approved and when." |
| `deploy-prod` | "Same CDK deploy, same config — but targeting the production account via a different context." |

**Key message:**
> "Feature branches get lint, test, build — so your PRs always have feedback. Deployment only happens after merge to main."

---

### Part 2: OIDC Auth — No Credentials in the Repo (2 minutes)

**Show the `assume-aws-role` command in the config:**

> "This is how we authenticate. No AWS access keys anywhere — not in the config, not in environment variables, not stored in CircleCI."

**Explain the flow:**

> "CircleCI generates a short-lived OIDC token → exchanges it with AWS STS → gets temporary credentials that expire after the job. If someone gets access to the config file, they get nothing — there are no secrets in it."

**Show the context in CircleCI UI (Organization Settings → Contexts):**

> "The role ARN lives here — in a CircleCI context with access restrictions. Only this project, only the main branch, can use the production context."

**Key message:**
> "Zero static credentials. If a developer leaves, you don't rotate anything. The OIDC trust handles identity."

---

### Part 3: The Handoff Boundary (2 minutes)

**Show the diagram from the steering file (or draw on whiteboard):**

```
CircleCI owns:  when to deploy, who can approve, what runs in what order
CDK owns:       what infrastructure exists, how resources are configured
Handoff point:  the `cdk deploy` command
```

> "Your team manages the CDK stacks — that's your infrastructure. The pipeline orchestration is handled by this CircleCI config. You don't need to understand CircleCI to modify your infrastructure, and you don't need to understand CDK to change the pipeline flow."

**Show what happens on failure:**

> "If CDK deploy fails — say a resource limit is hit or a permission is missing — CloudFormation automatically rolls back the stack. CircleCI marks the job red. You investigate in the CloudFormation console, not in CircleCI. Clean separation."

---

### Part 4: What Your Team Gets (1 minute)

> "When you adopt this, here's what you get out of the box without writing anything:"

- OIDC auth (no credential management)
- Lint + test + build on every PR
- CDK synth as a build-time check
- Automatic dev deploy on merge to main
- Manual gate before production
- Test results and coverage in CircleCI UI
- CDK outputs stored as pipeline artifacts

> "And here's what you DON'T have to do:"

- Write pipeline YAML from scratch
- Figure out OIDC configuration
- Set up approval workflows
- Configure caching
- Decide on job naming

---

### Part 5: Adoption Path (1 minute)

> "To adopt this for your project:"

1. We copy one config file into your repo
2. You set up two contexts in CircleCI (one-time, 5 minutes)
3. Your CDK app deploys automatically on every merge to main

> "You're already using CDK. You already have the OIDC trust established. The only new piece is this pipeline config — and it's ready to go."

---

## Live Trigger (optional — if time allows)

If you want to show a real pipeline run:

```bash
# Make a trivial change
echo "# demo" >> README.md
git add . && git commit -m "demo: trigger pipeline"
git push origin main
```

Then switch to CircleCI UI and watch the jobs light up in real-time.

---

## Anticipated Questions

**"Can we customize the lint/test tools?"**
> Yes — the commands are plain shell commands in the config. Swap `ruff` for `flake8`, add `pylint`, whatever your team prefers. The structure stays the same.

**"What if we have multiple CDK apps / stacks?"**
> `cdk deploy --all` handles that. It deploys every stack in your CDK app in dependency order. No pipeline changes needed.

**"Can we add a staging environment later?"**
> Yes — add a context (`aws-oidc-staging`), add `deploy-staging` and `approve-staging` jobs. We kept it to two environments because that's what exists today.

**"Who can approve production?"**
> Anyone with access to the CircleCI project. If you want to restrict approvers, CircleCI supports approval restrictions at the org level.

**"What happens if I push to a feature branch?"**
> Lint, test, and build run — you get PR feedback. No deployment happens. Only merges to main trigger deploys.

**"Is this tied to your AI tooling?"**
> No. This is a standard CircleCI config file. The AI tooling (steering file) ensures future changes stay consistent, but the config itself runs without any AI dependency. It's just YAML.

---

## After the Demo

- Share the sample config file for their review
- Offer: "We can do a pairing session to install this in your actual repo"
- Timeline: "If the config looks right, we can have your first real pipeline running within a day"
