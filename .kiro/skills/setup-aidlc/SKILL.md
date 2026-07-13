---
name: setup-aidlc
description: Set up AI-DLC (AI-Driven Development Life Cycle) in the current project. Use when you need to install or update AI-DLC workflows, configure IDE steering files, or bootstrap a project with AI-DLC support.
---

# Skill: Setup AI-DLC

Set up AI-DLC (AI-Driven Development Life Cycle) in the current project. This skill automates the official AI-Assisted Setup workflow from [awslabs/aidlc-workflows](https://github.com/awslabs/aidlc-workflows).

## Usage

Invoke this skill to configure AI-DLC in any project. The skill is idempotent — safe to run multiple times (it will overwrite/update existing setup).

## Optional: Version

If the user specifies a version (e.g., "set up AI-DLC v1.0.0"), use that version. Otherwise, default to the **latest** release.

---

## Instructions

Perform the following steps:

### 1. Download the AI-DLC release

Determine the download URL:

- **If a specific version is requested**, construct the URL directly:
  ```
  https://github.com/awslabs/aidlc-workflows/releases/download/v<VERSION>/ai-dlc-rules-v<VERSION>.zip
  ```

- **If no version specified (default to latest)**, use the GitHub API:
  ```bash
  curl -sL https://api.github.com/repos/awslabs/aidlc-workflows/releases/latest \
    | grep -o '"browser_download_url": *"[^"]*"' \
    | head -1 \
    | cut -d'"' -f4
  ```

Then download, extract, and install:

```bash
curl -sL -o /tmp/aidlc-rules.zip "<DOWNLOAD_URL>"
unzip -o /tmp/aidlc-rules.zip -d /tmp/aidlc-release
mkdir -p .aidlc
rm -rf .aidlc/aidlc-rules
cp -r /tmp/aidlc-release/aidlc-rules .aidlc/aidlc-rules
rm -rf /tmp/aidlc-rules.zip /tmp/aidlc-release
```

### 2. Create the appropriate rules/steering file

Auto-detect which IDE or agent is running and create the corresponding file. Pick the **first match**:

| IDE / Agent | File to create |
|---|---|
| Kiro IDE or Kiro CLI | `.kiro/steering/ai-dlc.md` |
| Amazon Q Developer | `.amazonq/rules/ai-dlc.md` |
| Antigravity | `.agent/rules/ai-dlc.md` |
| Cursor | `.cursor/rules/ai-dlc.mdc` (with frontmatter — see below) |
| Cline | `.clinerules/ai-dlc.md` |
| Claude Code | `CLAUDE.md` |
| GitHub Copilot | `.github/copilot-instructions.md` |
| Any other agent | `AGENTS.md` |

**File content** (for all except Cursor):

```
When the user invokes AI-DLC, read and follow
`.aidlc/aidlc-rules/aws-aidlc-rules/core-workflow.md` to start the workflow.
```

**For Cursor only**, prepend YAML frontmatter:

```
---
description: "AI-DLC workflow"
alwaysApply: true
---

When the user invokes AI-DLC, read and follow
`.aidlc/aidlc-rules/aws-aidlc-rules/core-workflow.md` to start the workflow.
```

### 3. Update .gitignore

Unless the user explicitly asks you **not** to:

- If `.gitignore` exists and does not already contain `.aidlc`, append `.aidlc` to it.
- If `.gitignore` does not exist, create it with `.aidlc` as its content.
- If `.aidlc` is already in `.gitignore`, do nothing.

### 4. Confirm

Tell the user:
- Which steering/rules file was created (and for which IDE)
- That `.aidlc` is gitignored (or that it was skipped if they asked not to)
- The AI-DLC version that was installed

---

## Idempotency

This skill is safe to run multiple times:
- `.aidlc/aidlc-rules/` is replaced with the freshly downloaded version on each run.
- The steering/rules file is overwritten (content is static).
- `.gitignore` is only appended to if `.aidlc` is not already present.

## Platform Notes

- This skill uses Unix commands (`curl`, `unzip`, `cp`, `rm`). It works on **macOS and Linux**.
- **For Windows**, see [`setup-aidlc-windows`](../setup-aidlc-windows/SKILL.md) which supports PowerShell, CMD, and Git Bash.
