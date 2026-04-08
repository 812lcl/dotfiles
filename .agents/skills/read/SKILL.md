---
name: read
description: Invoke when given any URL, web page link, or PDF to read. Fetches the content as clean Markdown via proxy cascade and saves to Downloads. Not for local files already in the repo.
version: 3.2.0
allowed-tools:
  - Bash
  - Read
  - Write
---

# Read: Fetch Any URL or PDF as Markdown

Convert any URL or local PDF to clean Markdown and save it.

## Routing

| Input | Method |
|-------|--------|
| `feishu.cn`, `larksuite.com` | Feishu API script |
| `.pdf` URL or local PDF path | PDF extraction |
| Everything else | Run `scripts/fetch.sh {url}` (proxy cascade with auto-fallback) |

After routing, load `references/read-methods.md` to get the specific commands for the chosen method, then execute.

## Output Format

```
Title:  {title}
Author: {author} (if available)
Source: {platform}
URL:    {original url}

Summary
{3-5 sentence summary}

Content
{full Markdown, truncated at 200 lines if long}
```

## Saving

Save to `~/Downloads/{title}.md` with YAML frontmatter by default.
Skip only if user says "just preview" or "don't save". Tell the user the saved path.

After saving and reporting the path, stop. Do not analyze, comment on, or discuss the content unless asked. If content was truncated at 200 lines, say so and offer to continue.

## Notes

- r.jina.ai and defuddle.md require no API key
- Network failures: prepend local proxy env vars if available
- Long content: `| head -n 200` to preview first
- GitHub URLs: prefer `gh` CLI over fetching directly
