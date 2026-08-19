# Security policy

Do not open a public issue containing credentials, private data, or an unpatched exploit.

For a suspected secret leak, malicious source URL, cross-site scripting issue, workflow-permission problem, or supply-chain concern, use GitHub's private vulnerability reporting for this repository. Include the affected file or URL, reproduction steps, and potential impact.

Public metadata corrections and broken links are not security issues; use the issue templates instead.

## Supported version

Only the current `main` branch and the currently deployed GitHub Pages version are supported.

## Secrets

API keys belong in GitHub Actions secrets. They must never be placed in `web/`, tracked data, workflow logs, issue comments, or pull requests. If a token is exposed, revoke it immediately; deleting the text later is not sufficient.
