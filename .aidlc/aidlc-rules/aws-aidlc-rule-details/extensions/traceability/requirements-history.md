# Requirements History and Traceability Rules

## Overview

These traceability rules are MANDATORY cross-cutting constraints that ensure AI-DLC workflow artifacts are preserved across multiple runs. They prevent overwriting of previous requirements, designs, and decisions — maintaining a complete project history without relying on git archaeology.

**Enforcement**: At each applicable stage, the model MUST verify compliance with these rules before presenting the stage completion message to the user.

### Blocking Traceability Finding Behavior

A **blocking traceability finding** means:
1. The finding MUST be listed in the stage completion message under a "Traceability Findings" section with the TRACE rule ID and description
2. The stage MUST NOT present the "Continue to Next Stage" option until all blocking findings are resolved
3. The model MUST present only the "Request Changes" option with a clear explanation of what needs to change
4. The finding MUST be logged in the shared `aidlc-docs/audit.md` with the TRACE rule ID, description, feature slug, and stage context

### Default Enforcement

All rules in this document are **blocking** by default. If any rule's verification criteria are not met, it is a blocking traceability finding — follow the blocking finding behavior defined above.

---

## Rule TRACE-01: Feature-Scoped Documentation Directories

**Rule**: Each AI-DLC workflow run MUST use a unique feature-scoped subdirectory under `aidlc-docs/` rather than overwriting shared paths. The directory structure MUST be:

```
aidlc-docs/
├── <feature-slug>/              # e.g., "setup-aidlc", "data-pipeline-ingestion"
│   ├── inception/
│   │   ├── requirements/
│   │   ├── plans/
│   │   ├── user-stories/
│   │   └── application-design/
│   └── construction/
│       ├── plans/
│       ├── build-and-test/
│       └── <unit-name>/
├── aidlc-state.md               # Shared state tracking (current feature context)
├── audit.md                     # Shared audit log (append-only across all features)
└── requirements-index.md        # Consolidated index (see TRACE-02)
```

The `<feature-slug>` MUST be derived from the user's initial request during Workspace Detection:
- Lowercase, hyphen-separated
- Concise but descriptive (e.g., `setup-aidlc`, `s3-ingestion-pipeline`, `user-auth-service`)
- Confirmed with the user before creating directories

**Verification**:
- No AI-DLC artifacts are written to `aidlc-docs/inception/` or `aidlc-docs/construction/` directly (must be under a feature slug)
- Each workflow run has its own `aidlc-docs/<feature-slug>/` directory
- Previous feature directories are never modified or deleted by subsequent runs
- The feature slug is confirmed with the user during Workspace Detection

---

## Rule TRACE-02: Consolidated Requirements Index

**Rule**: A consolidated requirements index MUST be maintained at `aidlc-docs/requirements-index.md`. After each Requirements Analysis stage completes, the model MUST append an entry to this index. The index provides a single-file overview of all requirements ever captured in this project.

Index format:

```markdown
# Requirements Index

| # | Feature | Date | Type | Scope | Status | Requirements File |
|---|---|---|---|---|---|---|
| 1 | setup-aidlc | 2026-06-24 | New Feature | Single Component | Complete | [Link](setup-aidlc/inception/requirements/requirements.md) |
| 2 | <next-feature> | <date> | <type> | <scope> | <status> | [Link](<slug>/inception/requirements/requirements.md) |
```

**Verification**:
- `aidlc-docs/requirements-index.md` exists after the first Requirements Analysis stage completes
- Each completed Requirements Analysis adds exactly one row to the index
- The index entry links to the feature-scoped requirements file (not a generic path)
- Previous index entries are never modified or removed
- Status is updated to "Complete" when the full workflow finishes for that feature

---

## Rule TRACE-03: No Overwrite of Previous Artifacts

**Rule**: AI-DLC workflow artifacts from previous runs MUST NOT be overwritten, deleted, or modified. Each run operates exclusively within its own feature-scoped directory. Specifically:

- The model MUST NOT write to any `aidlc-docs/<other-feature>/` directory
- The model MUST NOT delete or rename previous feature directories
- The model MUST NOT modify `requirements-index.md` entries for other features (only append new entries or update status of the current feature)
- `audit.md` at `aidlc-docs/audit.md` is append-only across all workflow runs

**Verification**:
- No file operations target `aidlc-docs/<other-feature-slug>/` directories
- Previous feature directories remain intact after a new workflow run
- `requirements-index.md` only has additions (no edits to previous rows except status updates for the current feature)

---

## Rule TRACE-04: Feature Slug Confirmation

**Rule**: During Workspace Detection, after analyzing the user's request, the model MUST propose a feature slug and get explicit user confirmation before creating any `aidlc-docs/` directories. The slug is used for the entire workflow run.

The confirmation MUST include:
- The proposed slug
- A one-line description of the feature
- The full path that will be created: `aidlc-docs/<slug>/`

Example:
```
I'll track this work under: aidlc-docs/setup-aidlc/
Feature: Reusable Kiro skill for AI-DLC setup

Does this feature name work, or would you prefer a different slug?
```

**Verification**:
- The feature slug is explicitly confirmed by the user before any aidlc-docs files are created
- The slug appears in `aidlc-docs/aidlc-state.md` under Project Information
- No aidlc-docs directories are created before slug confirmation

---

## Enforcement Integration

These rules apply to the following AI-DLC stages:

| Stage | Applicable Rules | Enforcement |
|---|---|---|
| Workspace Detection | TRACE-01, TRACE-04 | Feature slug must be confirmed, directory structure must be scoped |
| Requirements Analysis | TRACE-01, TRACE-02, TRACE-03 | Requirements written to feature directory, index updated |
| All Subsequent Stages | TRACE-01, TRACE-03 | All artifacts written to feature directory, no cross-feature writes |

At each applicable stage:
- Evaluate all TRACE rule verification criteria against file operations performed
- Include a "Traceability Compliance" section in the stage completion summary
- If any rule is non-compliant, this is a blocking finding — follow the blocking finding behavior defined in the Overview
