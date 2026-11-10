---
name: readwise-mcp
description: Compatibility entry for legacy readwise-mcp requests; routes Readwise and Reader operations to the local CLI
---

# Readwise CLI compatibility entry

Follow [readwise-cli](../readwise-cli/SKILL.md) and use the existing authenticated `readwise` command. The `readwise-mcp` name remains only for older references; Readwise MCP is retired on this machine.

Use `readwise <subcommand> --help` for current options and `--json` for structured results. For example, list Reader documents with `readwise reader-list-documents --location new --limit 10 --json`, or list highlights with `readwise readwise-list-highlights --page-size 20 --json`.

Do not install or re-register a Readwise MCP server through this compatibility entry. CLI connection errors should be reported as CLI errors while preserving the existing authentication.
