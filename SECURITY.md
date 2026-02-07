# Security Policy

## Reporting a Vulnerability

**Please do NOT report security vulnerabilities through public GitHub issues.**

If you discover a security vulnerability in RAGLeakLab, please report it responsibly:

1. **Email**: Send details to **mb050574@gmail.com**
2. **Include**:
   - Description of the vulnerability
   - Steps to reproduce
   - Potential impact
   - Any suggested fixes (optional)

We will acknowledge receipt within 48 hours and provide a detailed response within 7 days.

## What to Report

- Vulnerabilities in RAGLeakLab code
- Misconfigurations that could lead to security issues
- Dependencies with known vulnerabilities
- SSRF or injection vulnerabilities in HTTP target handling

## What NOT to Report in Public Issues

- Active exploits or PoC code
- Credentials, API keys, or secrets
- Exact steps to reproduce before a fix is available
- Customer or user data

## Scope

This policy covers the RAGLeakLab codebase. For vulnerabilities in:

- **Dependencies**: Report to the upstream project
- **Test data**: Our test corpora are synthetic and contain no real secrets

## Supported Versions

| Version | Supported          |
|---------|--------------------|
| 1.0.x   | ✅ Yes (current)   |
| 0.1.x   | ⚠️ Security only   |

## Security Features

RAGLeakLab includes security hardening:

- **SSRF protection**: URL validation for HTTP targets
- **Secret redaction**: PII/credentials masked in reports
- **Input validation**: Strict schema enforcement

See [docs/SECURITY_TOOLING.md](docs/SECURITY_TOOLING.md) for details.

## Acknowledgments

We appreciate responsible disclosure. Contributors who report valid vulnerabilities
will be acknowledged in our release notes (with permission).
