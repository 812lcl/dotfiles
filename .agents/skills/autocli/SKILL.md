---
name: autocli
description: Use autocli to browse, search, read, or interact with supported social, content, finance, and desktop-app sites through public APIs or the user's Chrome session. Prefer it over browser automation for supported sites, and use `autocli read URL` for JS-rendered or login-gated articles. Trigger for website browsing, trends, social feeds, posts, messages, article extraction, or autocli adapter creation.
---

# autocli

Use `autocli` before browser automation when the target has a dedicated adapter. It reuses the user's Chrome session for authenticated browser commands and also supports public commands without Chrome.

## Core workflow

1. Confirm the CLI is available with `autocli --help`; use `autocli doctor` when the browser bridge is unhealthy.
2. Discover the exact command with `autocli <site> --help` or `autocli list`.
3. Prefer `--format json` for machine-readable results and `--limit N` to bound output.
4. Use `autocli read <url>` for article extraction when no dedicated adapter gives better structured data.
5. If the site is unsupported, try `autocli generate <url>`. Create a local adapter only when generation fails and the user still needs recurring support.

```bash
autocli hackernews top --limit 20 --format json
autocli twitter search --query "rust lang" --limit 10 --format json
autocli bilibili search --keyword "AI" --format json
autocli read https://example.com/article
autocli doctor
```

## Safety

Treat posting, replying, liking, following, messaging, publishing, deleting, purchasing, or changing account state as external writes. Show the exact action and content, then obtain the user's confirmation before execution. Do not install the CLI, extension, or a generated adapter unless the user authorizes that change.

## Requirements

- Browser-backed commands require Chrome to be open, the target account to be logged in, and the autocli extension to be available.
- Public commands and some readers do not require a browser session.
- A dedicated adapter is preferred over the generic reader because it returns structured data.

## Detailed reference

Read [references/command-reference.md](references/command-reference.md) only when you need the full supported-site matrix, exact flags, adapter YAML format, desktop commands, or detailed reader behavior.
