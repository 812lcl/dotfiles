---
name: session-provider-inspect
description: Codex-only skill for inspecting a Codex session's recorded creation-time and latest observable provider/model, comparing them, and reporting whether provider or model changed. Use only when the current runtime is Codex and the user asks which provider or model a Codex session used, whether a resumed Codex session switched providers, or why a Codex session still consumes a different provider's quota. Do not trigger or run this skill for other agents, generic session logs, or non-Codex runtimes.
---

# Codex Session Provider Inspector

Use the bundled read-only script to inspect Codex's local session JSONL. The
script is intentionally fail-closed outside a Codex runtime: it requires
`CODEX_SESSION_ID` or `CODEX_THREAD_ID`, even when a session UUID is supplied
explicitly. It reads only `session_meta` and `thread_settings_applied` records
under `$CODEX_HOME/sessions` (default: `~/.codex`). It never reads `auth.json`,
prints credentials, or prints session prompts/responses.

## Commands

Run from any directory:

```bash
python3 <skill-dir>/scripts/inspect_session_provider.py --pretty
```

The default session ID comes from `CODEX_SESSION_ID`, then `CODEX_THREAD_ID`.
If neither is set, the script chooses the newest session file and reports that
fallback in `warnings`.

Inspect a specific session:

```bash
python3 <skill-dir>/scripts/inspect_session_provider.py \
  01a0d20e-ca6b-7b30-b6fe-4a4c12736b67 --pretty
```

Useful options:

```text
--codex-home PATH   Read a different Codex home.
--session-id UUID   Specify the session ID instead of the positional argument.
--pretty            Human-readable JSON (the default output is compact JSON).
--show-path         Include the selected local JSONL path in the result.
```

## Interpretation

- `created.provider` comes from `session_meta.payload.model_provider`.
- `created.model` comes from `session_meta.payload.model` when present;
  otherwise it is the earliest model in `thread_settings_applied`. The
  `model_source` field makes this distinction explicit.
- `recent` is the last `thread_settings_applied` record in the JSONL. This is
  the latest provider/model setting that the local session log exposes; it is
  not a claim about an HTTP request that was blocked before reaching a
  provider.
- `changed.provider`, `changed.model`, and `changed.any` compare the creation
  snapshot with that latest observable setting.

Exit status is `0` for a parsed session, `1` when no usable session or required
metadata can be found or when the current process is not identifiable as
Codex, and `2` for invalid arguments.

## Validation

```bash
python3 -m unittest discover \
  -s <skill-dir>/tests -v
python3 <skill-dir>/scripts/inspect_session_provider.py \
  --session-id 01a0d20e-ca6b-7b30-b6fe-4a4c12736b67 --pretty
```
