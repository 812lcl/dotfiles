---
name: codex-env-doctor
description: Diagnose whether a Codex development environment is correctly configured and actually usable. Use whenever the user asks for a Codex environment check, doctor, setup validation, config.toml or shell/PATH diagnosis, Brain CLI/repo/hook/tools health, Chrome DevTools MCP availability, local skill integrity/discovery, Jenkins environment/API readiness, Aliyun CLI credential/API readiness, or Plane/glab readiness, even if they do not name this skill.
---

# Codex Environment Doctor

Use this skill to distinguish configuration presence from runtime usability. Keep diagnosis read-only: do not install packages, rewrite config, clean caches, sync repositories, or repair hooks unless the user separately authorizes a fix.

Requires macOS or Linux with an available Python 3.11+ interpreter and Codex CLI. Remote verification additionally requires network access.

## Runbook

1. Run `brain brief` before non-trivial diagnosis when Brain is available.
2. Locate this skill directory from the loaded `SKILL.md` path.
3. Run the bundled doctor in quick mode first:

   ```bash
   bash <skill-dir>/scripts/run_doctor.sh
   ```

4. For the complete check requested by this skill, run:

   ```bash
   bash <skill-dir>/scripts/run_doctor.sh --all
   ```

   `--all` enables read-only network checks for Brain, Jenkins, Aliyun STS, Plane, and GitLab, starts a temporary Chrome DevTools MCP process for JSON-RPC initialization plus `tools/list` and `list_pages`, and runs `codex doctor --json`. The probe disables usage-statistics watchdogs and terminates both its process group and uniquely tagged npx descendants.

5. Use JSON when another tool must consume the result:

   ```bash
   bash <skill-dir>/scripts/run_doctor.sh --all --json
   ```

6. If a custom Codex home or working directory is in scope, pass them explicitly:

   ```bash
   bash <skill-dir>/scripts/run_doctor.sh \
     --config /path/to/config.toml \
     --cwd /path/to/project \
     --network --mcp-probe
   ```

## Evidence boundaries

Report these states separately:

- `configured`: the setting exists and parses.
- `resolvable`: the configured shell environment can locate the command.
- `locally_verified`: a local command or protocol handshake succeeded.
- `remote_verified`: the current remote or authenticated API was queried.
- `runtime_exposed`: the current Codex session exposes and can invoke the tool or skill.

Do not promote one state into another. In particular:

- `codex mcp list` proves registration, not server startup or browser access.
- An MCP `initialize` response proves protocol startup, not that `list_pages` can reach Chrome.
- A clean Brain checkout against `origin/*` is only a local snapshot until `--network` compares the remote SHA.
- A successful `brain tools list` proves inventory readability, not that production-query or deployment tools were executed. The doctor only checks entrypoint syntax, executable bits, interpreters, Python imports, and local references.
- A valid skill directory is not proof that the current session exposed it. Codex may shorten or omit entries when the initial skill metadata budget is crowded.
- Jenkins variables in the workspace `.env`, current Codex process, and login shell are distinct states. The helper can be usable by sourcing its private `.env` even when Codex does not directly inherit the variables.
- Jenkins local configuration is not proof of valid credentials. Only `--network` or `--all` queries the read-only `whoAmI` and root APIs; it never lists credential values or triggers a job.
- Aliyun profile presence is not proof of valid credentials. Only `--network` or `--all` calls read-only `sts GetCallerIdentity`; the identity response and credential values are discarded and never reported.
- `glab auth status` and `plane-cli config show` prove local configuration; authenticated API checks require `--network`.

## Jenkins checks

The doctor derives the Jenkins contract from `brain/tools/jenkins.sh` and expects `JENKINS_URL`, `JENKINS_USER`, and `JENKINS_TOKEN`. It reports only required variable names, presence flags, file mode, URL validity, and sanitized API status.

- `jenkins.tool` validates the helper, executable bit, shell syntax, required variable contract, and local dependencies.
- `jenkins.env.file` validates the helper's workspace `.env` without executing it and warns when credential-file permissions are broader than owner-only.
- `jenkins.env.codex` and `jenkins.env.login_shell` show whether variables are directly available in those environments. Missing direct inheritance is a warning when the helper's private source remains healthy.
- `jenkins.api` stays `UNKNOWN` in quick mode. With `--network`, it uses HTTP Basic authentication in-process, confirms an authenticated identity, then reads the root API. It does not invoke the helper's `build` command.

## Aliyun and Brain tools checks

- `aliyun.cli` validates command resolution in the Codex child PATH and runs only `aliyun version`.
- `aliyun.config` parses the selected profile or supported environment credential contract, checks required fields and private file permissions, and reports only booleans, mode, and missing field names.
- `aliyun.api` stays `UNKNOWN` in quick mode. With `--network`, it calls read-only `aliyun sts GetCallerIdentity`, discards the response, and reports only success or a generic error class.
- `brain.tools.inventory` validates `brain tools list` and the top-level entrypoint inventory.
- `brain.tools.integrity` checks top-level Python/shell entrypoints and `_lib` files for readability, shebangs, executable bits, and syntax. It ignores README files, tests, `__pycache__`, and `.pyc` files.
- `brain.tools.dependencies` statically checks interpreters, Python imports, and referenced `_lib` files. It never executes a Brain business tool, production query, build, deployment, or write operation.

## Skill checks

The bundled doctor follows current Codex discovery rules:

- repository `.agents/skills` directories from the working directory to the Git root;
- user `$HOME/.agents/skills`;
- admin `/etc/codex/skills`;
- Codex system skills when their local system root is present.

It validates required frontmatter, broken symlinks, directory/name mismatches, duplicate names, misplaced root directories, missing relative Markdown references, Python and shell script syntax, `[[skills.config]]` paths, lock JSON, and initial metadata pressure. Disabled `[[skills.config]]` paths are excluded from duplicate, entrypoint-size, metadata, and runtime-missing comparisons. Duplicate enabled names are a warning rather than a failure because Codex may expose both.

The script uses a fresh Codex app-server `skills/list` call with `forceReload=true` to prove that Codex can load the inventory. This probe temporarily disables MCP servers because skill discovery does not require them. Treat fresh runtime load errors and missing names as the verdict; metadata character count remains diagnostic only when runtime loading is complete. After it runs, separately compare that inventory with the skills visible to the already-running session when its registry is available. If direct comparison is unavailable, keep `skills.current_session_exposure` as `UNKNOWN`; do not infer it from a fresh process.

## Interpreting results

- `PASS`: the claimed layer was verified.
- `WARN`: usable but risky, stale, ambiguous, context-dependent, or degraded.
- `FAIL`: a required capability is broken or the configured runtime cannot use it.
- `UNKNOWN`: the check was intentionally skipped or the current interface cannot establish it.

Treat non-TTY `TERM=dumb` from an agent subprocess as contextual rather than a host terminal failure. Preserve other `codex doctor` failures.

Lead the final answer with the overall result and the highest-impact failures. Then list verified healthy boundaries, warnings/unknowns, and exact remediation commands. Never print secrets, raw auth payloads, Brain's absolute repository path, or full subprocess environments.

## Common targeted runs

```bash
# Local config, shell, Brain tools, Aliyun config, skill, and CLI checks only
bash <skill-dir>/scripts/run_doctor.sh

# Refresh remote truth for Brain, Jenkins, Aliyun STS, Plane, and GitLab
bash <skill-dir>/scripts/run_doctor.sh --network

# Prove Chrome DevTools MCP startup and browser operation
bash <skill-dir>/scripts/run_doctor.sh --mcp-probe

# Include the built-in Codex doctor and normalize non-TTY-only findings
bash <skill-dir>/scripts/run_doctor.sh --codex-doctor
```

## Validation

When this skill itself changes, run:

```bash
DOCTOR_PYTHON=$(bash <skill-dir>/scripts/run_doctor.sh --print-python)
"$DOCTOR_PYTHON" -m unittest discover -s <skill-dir>/tests -v
bash <skill-dir>/scripts/run_doctor.sh --json
```
