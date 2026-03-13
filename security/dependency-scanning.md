# Dependency Scanning

# Dependency Scanning and Supply-Chain Security

## Objectives
- Detect known vulnerabilities (CVEs) in dependencies.
- Prevent malicious or compromised packages from entering builds.
- Enforce minimum hygiene for PRs and releases.

## Required controls (baseline)
Backend (Python):
- Pin dependencies (requirements.txt is acceptable; lockfile preferred if using poetry/pip-tools).
- Run:
  - SAST/linting (e.g., bandit where appropriate)
  - Dependency vulnerability scanning (e.g., pip-audit or safety)
- Fail builds on high severity vulnerabilities unless explicitly approved.

Frontend (Node):
- Lockfile required (package-lock.json / pnpm-lock.yaml / yarn.lock).
- Use npm audit (or equivalent) in CI.
- Block known critical vulnerabilities.

Containers:
- Scan images (Trivy or equivalent) for OS and dependency CVEs.

## Exception process
- Any exception must:
  - list package, CVE, severity
  - include compensating controls
  - include expiry date for re-evaluation

