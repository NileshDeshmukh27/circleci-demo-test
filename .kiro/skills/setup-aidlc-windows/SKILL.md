---
name: setup-aidlc-windows
description: Set up AI-DLC (AI-Driven Development Life Cycle) on Windows. Use when you need to install or update AI-DLC workflows on a Windows machine. Supports PowerShell, CMD (batch), and Git Bash.
---

# Skill: Setup AI-DLC (Windows)

Set up AI-DLC (AI-Driven Development Life Cycle) in the current project on Windows. This skill automates the official AI-Assisted Setup workflow from [awslabs/aidlc-workflows](https://github.com/awslabs/aidlc-workflows) using Windows-native tools.

## Usage

Invoke this skill to configure AI-DLC in any project running on Windows. The skill is idempotent — safe to run multiple times (it will overwrite/update existing setup).

## Optional: Version

If the user specifies a version (e.g., "set up AI-DLC v1.0.0"), use that version. Otherwise, default to the **latest** release.

---

## Shell Selection

This skill supports three Windows shell environments. **Choose the appropriate shell based on what is available in the environment:**

| Shell | When to Use | Prerequisites |
|---|---|---|
| **PowerShell** | Default choice for Windows 10/11 | PowerShell 5.1+ (built-in) or PowerShell 7+ |
| **CMD (batch)** | Fallback when PowerShell is unavailable or restricted | Windows 10+ (for built-in `curl` and `tar`) |
| **Git Bash** | When Git for Windows is installed | Git for Windows installed |

**Selection priority**: PowerShell → CMD → Git Bash

**Detection guidance for agents:**
- If PowerShell is available → use **PowerShell**
- If PowerShell is unavailable or blocked by policy → use **CMD**
- If Git Bash is detected (e.g., running inside Git Bash terminal, or `bash` is available via Git) → use **Git Bash** (same commands as macOS/Linux skill)

---

## Instructions

### 1. Download the AI-DLC release

Determine the download URL:

- **If a specific version is requested**, construct the URL directly:
  ```
  https://github.com/awslabs/aidlc-workflows/releases/download/v<VERSION>/ai-dlc-rules-v<VERSION>.zip
  ```

- **If no version specified (default to latest)**, query the GitHub API:


#### PowerShell

```powershell
$release = Invoke-RestMethod -Uri "https://api.github.com/repos/awslabs/aidlc-workflows/releases/latest"
$downloadUrl = $release.assets[0].browser_download_url
```

#### CMD

```cmd
curl -sL https://api.github.com/repos/awslabs/aidlc-workflows/releases/latest -o "%TEMP%\aidlc-latest.json"
for /f "usebackq tokens=2,* delims=:" %%a in (`findstr /i "\"browser_download_url\"" "%TEMP%\aidlc-latest.json"`) do if not defined DOWNLOAD_URL set "DOWNLOAD_URL=%%b"
set "DOWNLOAD_URL=%DOWNLOAD_URL:"=%"
set "DOWNLOAD_URL=%DOWNLOAD_URL:,=%"
set "DOWNLOAD_URL=%DOWNLOAD_URL: =%"
del "%TEMP%\aidlc-latest.json"

#### Git Bash

```bash
curl -sL https://api.github.com/repos/awslabs/aidlc-workflows/releases/latest \
  | grep -o '"browser_download_url": *"[^"]*"' \
  | head -1 \
  | cut -d'"' -f4
```

Then download, extract, and install:

#### PowerShell

```powershell
$tmpZip = Join-Path $env:TEMP "aidlc-rules.zip"
$tmpDir = Join-Path $env:TEMP "aidlc-release"
Invoke-WebRequest -Uri $downloadUrl -OutFile $tmpZip
if (Test-Path $tmpDir) { Remove-Item -Recurse -Force $tmpDir }
Expand-Archive -Path $tmpZip -DestinationPath $tmpDir -Force
if (-not (Test-Path ".aidlc")) { New-Item -ItemType Directory -Path ".aidlc" | Out-Null }
if (Test-Path ".aidlc\aidlc-rules") { Remove-Item -Recurse -Force ".aidlc\aidlc-rules" }
Copy-Item -Recurse -Force (Join-Path $tmpDir "aidlc-rules") ".aidlc\aidlc-rules"
Remove-Item -Force $tmpZip
Remove-Item -Recurse -Force $tmpDir
```

#### CMD

```cmd
curl -sL -o %TEMP%\aidlc-rules.zip "%DOWNLOAD_URL%"
if exist %TEMP%\aidlc-release rmdir /s /q %TEMP%\aidlc-release
mkdir %TEMP%\aidlc-release
tar -xf %TEMP%\aidlc-rules.zip -C %TEMP%\aidlc-release
if not exist .aidlc mkdir .aidlc
if exist .aidlc\aidlc-rules rmdir /s /q .aidlc\aidlc-rules
xcopy /e /i /q /y %TEMP%\aidlc-release\aidlc-rules .aidlc\aidlc-rules
del %TEMP%\aidlc-rules.zip
rmdir /s /q %TEMP%\aidlc-release
```

#### Git Bash

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

**Note on creating directories**: Use `mkdir` (CMD), `New-Item -ItemType Directory` (PowerShell), or `mkdir -p` (Git Bash) to create parent directories as needed.

### 3. Update .gitignore

Unless the user explicitly asks you **not** to:

#### PowerShell

```powershell
if (Test-Path ".gitignore") {
    $content = Get-Content ".gitignore" -Raw
    if ($content -notmatch '(?m)^\.aidlc$') {
        Add-Content -Path ".gitignore" -Value "`n.aidlc"
    }
} else {
    Set-Content -Path ".gitignore" -Value ".aidlc"
}
```

#### CMD

```cmd
if exist .gitignore (
    findstr /x ".aidlc" .gitignore >nul 2>&1
    if errorlevel 1 (
        echo .aidlc >> .gitignore
    )
) else (
    echo .aidlc > .gitignore
)
```

#### Git Bash

```bash
if [ -f .gitignore ]; then
    grep -qx '\.aidlc' .gitignore || echo '.aidlc' >> .gitignore
else
    echo '.aidlc' > .gitignore
fi
```

### 4. Confirm

Tell the user:
- Which steering/rules file was created (and for which IDE)
- That `.aidlc` is gitignored (or that it was skipped if they asked not to)
- The AI-DLC version that was installed
- Which shell was used (PowerShell, CMD, or Git Bash)

---

## Idempotency

This skill is safe to run multiple times:
- `.aidlc/aidlc-rules/` is replaced with the freshly downloaded version on each run.
- The steering/rules file is overwritten (content is static).
- `.gitignore` is only appended to if `.aidlc` is not already present.

## Prerequisites by Shell

| Shell | Minimum Version | Ships With | Notes |
|---|---|---|---|
| PowerShell | 5.1+ | Windows 10/11 | Execution policy must allow scripts. Use `Set-ExecutionPolicy RemoteSigned -Scope CurrentUser` if restricted. |
| CMD | N/A | All Windows | Requires Windows 10+ for built-in `curl` and `tar`. On older Windows, install curl separately. |
| Git Bash | N/A | Git for Windows | Install from https://git-scm.com/download/win |

## Cross-Platform Note

For macOS and Linux, see the [`setup-aidlc`](../setup-aidlc/SKILL.md) skill which uses Unix commands (`curl`, `unzip`, `cp`, `rm`).
