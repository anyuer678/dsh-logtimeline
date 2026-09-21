# Security Policy

## Supported versions

This repository is maintained on a **portfolio / local-tool** basis.
Security fixes are applied on a best-effort basis to the default branch.

## Reporting a vulnerability

Please **do not** open a public issue for security vulnerabilities.

- Open a private GitHub Security Advisory on this repository, **or**
- Contact the maintainer via the GitHub profile of [anyuer678](https://github.com/anyuer678)

Include: affected version/commit, reproduction steps, impact, and any suggested fix.

## Scope notes

Many projects here are **not production multi-tenant systems**.
See each repository README for the honest capability boundary (`local-tool` / `portfolio` / `engine` / `archived`).
Do not deploy portfolio agents (e.g. lumen) or local MCP tools to the public internet.

## Secrets

- Never commit API keys, tokens, or `.env` files.
- Prefer environment variables or the local `keyvault` tooling.
- CI secret-scan workflows are enabled on several repositories; treat failures as blocking when `GITLEAKS_STRICT` is turned on.
