## Git Commit Policy

Git commit with GPG signature verification is mandatory. Do not skip this step.

- Every commit MUST be signed. Use `git commit` (not `git commit --no-gpg-sign`).
- If GPG signing fails (e.g., passphrase timeout), wait for the user to provide their passphrase and retry. Do NOT fall back to unsigned commits.
- Never use `--no-verify` to bypass hooks unless the user explicitly asks.
- Always verify the commit was signed successfully before pushing.

## Signing Not Configured

If git signing is not configured on the developer's machine:

- Do NOT attempt to commit without a signature. All commits must be signed.
- Do NOT fall back to unsigned commits under any circumstances.
- Direct the user to configure GPG signing by following the GitHub GPG signing guide: https://docs.github.com/en/authentication/managing-commit-signature-verification
- Wait for the user to confirm signing is configured before proceeding with any commits.
