# Security Policy

## Reporting a Vulnerability

If you discover a security vulnerability, please report it through [GitHub's private vulnerability reporting](https://github.com/johnwesley/dungeon_minus_one/security/advisories/new).

**Please do not open a public issue for security vulnerabilities.**

### What qualifies

- Authentication or authorization bypass
- Data exposure (other users' game state, credentials, PII)
- Server-side request forgery (SSRF)
- SQL injection or other injection attacks
- Cross-site scripting (XSS) in the web UI

### What doesn't qualify

- Game logic exploits (finding unintended puzzle solutions, sequence breaks)
- Prompt injection to make the narrator break character
- Issues requiring physical access to the server

### Response timeline

- **Acknowledgment**: Within 72 hours
- **Assessment**: Within 1 week
- **Fix**: Depends on severity, but we aim for prompt resolution

## Supported Versions

Only the latest release is supported with security updates.
