#!/usr/bin/env python3
"""Read-only health checks for a local Codex development environment."""

from __future__ import annotations

import argparse
import ast
import base64
import dataclasses
import datetime as dt
import importlib.util
import json
import os
import platform
import re
import selectors
import shlex
import shutil
import signal
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Iterable

try:
    import tomllib
except ImportError as exc:  # pragma: no cover - checked before normal execution
    raise SystemExit("Python 3.11+ is required (tomllib is unavailable)") from exc


STATUS_ORDER = {"PASS": 0, "UNKNOWN": 1, "WARN": 2, "FAIL": 3}
SECRET_KEY = re.compile(r"(?i)(api[_-]?key|authorization|credential|password|secret|token)")
FRONTMATTER_KEY = re.compile(r"^([A-Za-z0-9_-]+):\s*(.*)$")
SKILL_NAME = re.compile(r"^[a-z0-9][a-z0-9-]*$")
MARKDOWN_LINK = re.compile(r"\[[^\]]*\]\(([^)]+)\)")
ENV_ASSIGNMENT = re.compile(r"^\s*(?:export\s+)?([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.*)$")
JENKINS_ENV_KEYS = ("JENKINS_URL", "JENKINS_USER", "JENKINS_TOKEN")
ALIYUN_ENV_KEYS = (
    "ALIBABA_CLOUD_ACCESS_KEY_ID",
    "ALIBABA_CLOUD_ACCESS_KEY_SECRET",
)
ALIYUN_PROFILE_REQUIREMENTS = {
    "AK": ("access_key_id", "access_key_secret"),
    "StsToken": ("access_key_id", "access_key_secret", "sts_token"),
    "RamRoleArn": ("access_key_id", "access_key_secret", "ram_role_arn"),
    "EcsRamRole": (),
    "RsaKeyPair": ("key_pair_name", "private_key"),
    "RamRoleArnWithRoleName": ("access_key_id", "access_key_secret", "ram_role_name"),
    "External": ("process_command",),
    "ChainableRamRoleArn": ("source_profile", "ram_role_arn"),
    "CredentialsURI": ("credentials_uri",),
    "OIDC": ("oidc_provider_arn", "oidc_token_file", "ram_role_arn"),
    "CloudSSO": ("cloud_sso_sign_in_url",),
    "OAuth": ("oauth_site_type",),
}


@dataclasses.dataclass
class Check:
    id: str
    category: str
    status: str
    summary: str
    details: dict[str, Any] = dataclasses.field(default_factory=dict)
    remediation: str | None = None


@dataclasses.dataclass
class CommandResult:
    returncode: int
    stdout: str
    stderr: str
    duration_ms: int
    timed_out: bool = False


@dataclasses.dataclass
class SkillRecord:
    name: str
    description: str
    directory: Path
    skill_file: Path
    scope: str
    line_count: int
    enabled: bool = True


def run_command(
    args: list[str],
    *,
    timeout: float = 15,
    input_text: str | None = None,
    env: dict[str, str] | None = None,
    cwd: Path | None = None,
) -> CommandResult:
    started = time.monotonic()
    try:
        proc = subprocess.run(
            args,
            input=input_text,
            text=True,
            capture_output=True,
            timeout=timeout,
            env=env,
            cwd=str(cwd) if cwd else None,
            check=False,
        )
        return CommandResult(
            proc.returncode,
            proc.stdout,
            proc.stderr,
            int((time.monotonic() - started) * 1000),
        )
    except subprocess.TimeoutExpired as exc:
        stdout = exc.stdout.decode() if isinstance(exc.stdout, bytes) else (exc.stdout or "")
        stderr = exc.stderr.decode() if isinstance(exc.stderr, bytes) else (exc.stderr or "")
        return CommandResult(
            124,
            stdout,
            stderr,
            int((time.monotonic() - started) * 1000),
            timed_out=True,
        )
    except OSError as exc:
        return CommandResult(127, "", str(exc), int((time.monotonic() - started) * 1000))


def compact(text: str, limit: int = 320) -> str:
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    preferred = next((line for line in lines if "error" in line.lower()), None)
    value = preferred or (lines[-1] if lines else "no output")
    value = SECRET_KEY.sub("<redacted-key>", value)
    return value if len(value) <= limit else value[: limit - 3] + "..."


def load_toml(path: Path) -> dict[str, Any]:
    return tomllib.loads(path.read_text(encoding="utf-8"))


def load_env_assignments(path: Path, names: Iterable[str]) -> tuple[dict[str, str], list[str]]:
    wanted = set(names)
    values: dict[str, str] = {}
    invalid: list[str] = []
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeError):
        return values, sorted(wanted)
    for line in lines:
        match = ENV_ASSIGNMENT.match(line)
        if not match or match.group(1) not in wanted:
            continue
        name, raw = match.groups()
        try:
            tokens = shlex.split(raw, comments=True, posix=True)
        except ValueError:
            invalid.append(name)
            continue
        if len(tokens) > 1:
            invalid.append(name)
            continue
        values[name] = tokens[0] if tokens else ""
    return values, sorted(set(invalid))


def valid_jenkins_url(value: str | None) -> bool:
    if not value:
        return False
    try:
        parsed = urllib.parse.urlparse(value)
        username, password = parsed.username, parsed.password
    except ValueError:
        return False
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc) and not username and not password


def inspect_aliyun_config(path: Path, environ: dict[str, str]) -> dict[str, Any]:
    """Return credential readiness without returning credential or identity values."""
    env_present = sorted(name for name in ALIYUN_ENV_KEYS if environ.get(name))
    env_complete = len(env_present) == len(ALIYUN_ENV_KEYS)
    ignore_profile = environ.get("ALIBABA_CLOUD_IGNORE_PROFILE", "").upper() == "TRUE"
    details: dict[str, Any] = {
        "file_present": path.is_file(),
        "file_private": False,
        "profile_ignored": ignore_profile,
        "environment_credentials_complete": env_complete,
        "region_present": bool(environ.get("ALIBABA_CLOUD_REGION_ID")),
    }
    if ignore_profile:
        details["source"] = "environment" if env_complete else "missing"
        details["credentials_complete"] = env_complete
        return details
    if not path.is_file():
        details["source"] = "environment" if env_complete else "missing"
        details["credentials_complete"] = env_complete
        return details
    details["file_private"] = path.stat().st_mode & 0o077 == 0
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        details["source"] = "environment" if env_complete else "invalid_file"
        details["parse_ok"] = False
        details["credentials_complete"] = env_complete
        return details
    details["parse_ok"] = isinstance(data, dict)
    profiles = data.get("profiles", []) if isinstance(data, dict) else []
    profiles = profiles if isinstance(profiles, list) else []
    requested = environ.get("ALIBABA_CLOUD_PROFILE") or data.get("current")
    selected = next(
        (
            profile
            for profile in profiles
            if isinstance(profile, dict)
            and isinstance(requested, str)
            and profile.get("name") == requested
        ),
        None,
    )
    if not isinstance(selected, dict):
        details["source"] = "environment" if env_complete else "profile"
        details["profile_selected"] = False
        details["credentials_complete"] = env_complete
        return details
    mode = selected.get("mode")
    requirements = ALIYUN_PROFILE_REQUIREMENTS.get(mode) if isinstance(mode, str) else None
    missing = sorted(name for name in (requirements or ()) if not selected.get(name))
    known_mode = requirements is not None
    source_profile_resolves = True
    if mode == "ChainableRamRoleArn" and selected.get("source_profile"):
        source_profile_resolves = any(
            isinstance(profile, dict) and profile.get("name") == selected["source_profile"]
            for profile in profiles
        )
    profile_complete = known_mode and not missing and source_profile_resolves
    details.update(
        {
            "source": "profile" if profile_complete else ("environment" if env_complete else "profile"),
            "profile_selected": True,
            "mode": mode if known_mode else "unknown",
            "mode_supported": known_mode,
            "required_fields_present": not missing,
            "source_profile_resolves": source_profile_resolves,
            "credentials_complete": profile_complete or env_complete,
            "region_present": bool(selected.get("region_id") or environ.get("ALIBABA_CLOUD_REGION_ID")),
        }
    )
    if missing:
        details["missing_fields"] = missing
    return details


def classify_aliyun_error(result: CommandResult) -> str:
    if result.timed_out:
        return "timeout"
    text = f"{result.stderr}\n{result.stdout}".lower()
    if any(marker in text for marker in ("invalidaccesskey", "signaturedoesnotmatch", "securitytoken", "unauthorized")):
        return "authentication"
    if any(marker in text for marker in ("forbidden", "not authorized", "no permission", "accessdenied")):
        return "authorization"
    if any(marker in text for marker in ("timeout", "connection", "no such host", "network", "tls")):
        return "network"
    if any(marker in text for marker in ("throttl", "rate exceeded")):
        return "throttled"
    return "command_failed"


def probe_jenkins_api(credentials: dict[str, str], timeout: float = 20) -> dict[str, Any]:
    base_url = credentials["JENKINS_URL"].rstrip("/")
    raw_auth = f'{credentials["JENKINS_USER"]}:{credentials["JENKINS_TOKEN"]}'.encode()
    authorization = "Basic " + base64.b64encode(raw_auth).decode("ascii")

    def request_json(path: str, stage: str) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
        request = urllib.request.Request(
            base_url + path,
            headers={"Authorization": authorization, "Accept": "application/json", "User-Agent": "codex-env-doctor/1.0"},
        )
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                status = getattr(response, "status", 200)
                payload = response.read(65536)
        except urllib.error.HTTPError as exc:
            return None, {"stage": stage, "http_status": exc.code, "error_type": "HTTPError"}
        except urllib.error.URLError as exc:
            return None, {"stage": stage, "error_type": type(exc.reason).__name__}
        except (OSError, TimeoutError) as exc:
            return None, {"stage": stage, "error_type": type(exc).__name__}
        if status != 200:
            return None, {"stage": stage, "http_status": status, "error_type": "UnexpectedHTTPStatus"}
        try:
            data = json.loads(payload)
        except (json.JSONDecodeError, UnicodeDecodeError):
            return None, {"stage": stage, "http_status": status, "error_type": "InvalidJSON"}
        if not isinstance(data, dict):
            return None, {"stage": stage, "http_status": status, "error_type": "InvalidPayload"}
        return data, None

    identity, error = request_json("/whoAmI/api/json", "identity")
    if error:
        return {"status": "FAIL", "summary": "Jenkins identity API authentication failed", "details": error}
    identity_name = identity.get("name")
    authenticated = identity.get("authenticated") is True and isinstance(identity_name, str) and identity_name not in {"", "anonymous"}
    if not authenticated:
        return {
            "status": "FAIL",
            "summary": "Jenkins API responded without an authenticated identity",
            "details": {"identity_authenticated": False},
        }
    root, error = request_json("/api/json?tree=nodeName,mode", "root_api")
    if error:
        return {"status": "FAIL", "summary": "Jenkins identity is valid but the root API is unavailable", "details": error}
    return {
        "status": "PASS",
        "summary": "Jenkins credentials authenticated and the read-only root API succeeded",
        "details": {"identity_authenticated": True, "root_api_readable": isinstance(root, dict)},
    }


def is_relative_to(path: Path, parent: Path) -> bool:
    try:
        path.relative_to(parent)
        return True
    except ValueError:
        return False


def hook_commands(config: dict[str, Any], event: str) -> list[str]:
    hooks = config.get("hooks", {})
    if not isinstance(hooks, dict):
        return []
    entries = hooks.get(event, [])
    commands: list[str] = []
    if not isinstance(entries, list):
        return commands
    for entry in entries:
        nested = entry.get("hooks", []) if isinstance(entry, dict) else []
        for hook in nested if isinstance(nested, list) else []:
            if isinstance(hook, dict) and isinstance(hook.get("command"), str):
                commands.append(hook["command"])
    return commands


def parse_frontmatter(path: Path) -> tuple[dict[str, str], str | None]:
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        return {}, str(exc)
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return {}, "missing opening YAML frontmatter delimiter"
    try:
        end = next(i for i in range(1, len(lines)) if lines[i].strip() == "---")
    except StopIteration:
        return {}, "missing closing YAML frontmatter delimiter"
    data: dict[str, str] = {}
    i = 1
    while i < end:
        match = FRONTMATTER_KEY.match(lines[i])
        if not match:
            i += 1
            continue
        key, raw = match.groups()
        raw = raw.strip()
        if raw in {"|", ">", "|-", ">-", "|+", ">+"}:
            values: list[str] = []
            i += 1
            while i < end and (not lines[i].strip() or lines[i][:1].isspace()):
                if lines[i].strip():
                    values.append(lines[i].strip())
                i += 1
            data[key] = " ".join(values)
            continue
        if len(raw) >= 2 and raw[0] == raw[-1] and raw[0] in {"'", '"'}:
            raw = raw[1:-1]
        data[key] = raw
        i += 1
    return data, None


def discover_repo_root(cwd: Path) -> Path | None:
    result = run_command(["git", "rev-parse", "--show-toplevel"], cwd=cwd, timeout=5)
    if result.returncode != 0:
        return None
    candidate = Path(result.stdout.strip())
    return candidate if candidate.is_dir() else None


def skill_roots(cwd: Path, home: Path) -> list[tuple[str, Path]]:
    roots: list[tuple[str, Path]] = [("user", home / ".agents" / "skills")]
    repo_root = discover_repo_root(cwd)
    if repo_root:
        cursor = cwd.resolve()
        while True:
            roots.append(("repo", cursor / ".agents" / "skills"))
            if cursor == repo_root or cursor.parent == cursor:
                break
            cursor = cursor.parent
    roots.append(("admin", Path("/etc/codex/skills")))
    system_root = home / ".codex" / "skills" / ".system"
    if system_root.exists():
        roots.append(("system", system_root))
    unique: list[tuple[str, Path]] = []
    seen: set[str] = set()
    for scope, root in roots:
        key = str(root.resolve(strict=False))
        if key not in seen:
            seen.add(key)
            unique.append((scope, root))
    return unique


def validate_script_syntax(path: Path) -> str | None:
    try:
        if path.suffix == ".py":
            ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        elif path.suffix in {".sh", ".bash"}:
            result = run_command(["bash", "-n", str(path)], timeout=5)
            if result.returncode != 0:
                return compact(result.stderr)
    except (OSError, SyntaxError, UnicodeError) as exc:
        return str(exc)
    return None


def process_ids_matching(token: str) -> list[int]:
    result = run_command(["ps", "-axo", "pid=,command="], timeout=5)
    if result.returncode != 0:
        return []
    matches: list[int] = []
    for line in result.stdout.splitlines():
        match = re.match(r"\s*(\d+)\s+(.*)$", line)
        if match and token in match.group(2):
            pid = int(match.group(1))
            if pid != os.getpid():
                matches.append(pid)
    return matches


def terminate_tagged_processes(token: str) -> None:
    for sig in (signal.SIGTERM, signal.SIGKILL):
        pids = process_ids_matching(token)
        if not pids:
            return
        for pid in pids:
            try:
                os.kill(pid, sig)
            except ProcessLookupError:
                pass
        deadline = time.monotonic() + (2 if sig == signal.SIGTERM else 1)
        while time.monotonic() < deadline and process_ids_matching(token):
            time.sleep(0.05)


class Doctor:
    def __init__(self, args: argparse.Namespace):
        self.args = args
        self.home = Path.home()
        self.cwd = Path(args.cwd).expanduser().resolve()
        self.config_path = Path(args.config).expanduser()
        self.config: dict[str, Any] = {}
        self.checks: list[Check] = []
        self.effective_path = os.environ.get("PATH", os.defpath)

    def add(
        self,
        check_id: str,
        category: str,
        status: str,
        summary: str,
        details: dict[str, Any] | None = None,
        remediation: str | None = None,
    ) -> None:
        self.checks.append(Check(check_id, category, status, summary, details or {}, remediation))

    def executable(self, name: str) -> str | None:
        return shutil.which(name) or shutil.which(name, path=self.effective_path)

    def command_env(self) -> dict[str, str]:
        env = os.environ.copy()
        env["PATH"] = self.effective_path
        env["CODEX_HOME"] = str(self.config_path.parent)
        return env

    def app_server_command(self, codex: str, *, strict: bool = False, disable_mcp: bool = False) -> list[str]:
        command = [codex, "app-server"]
        if strict:
            command.append("--strict-config")
        if disable_mcp:
            servers = self.config.get("mcp_servers", {})
            if isinstance(servers, dict):
                for name, server in sorted(servers.items()):
                    if (
                        isinstance(name, str)
                        and re.fullmatch(r"[A-Za-z0-9_-]+", name)
                        and isinstance(server, dict)
                        and server.get("enabled", True) is not False
                    ):
                        command.extend(["-c", f"mcp_servers.{name}.enabled=false"])
        command.append("--stdio")
        return command

    def configured_skill_path(self, raw_path: str) -> Path:
        path = Path(raw_path).expanduser()
        if not path.is_absolute():
            path = self.config_path.parent / path
        return path.resolve(strict=False)

    def disabled_skill_paths(self) -> set[Path]:
        skills = self.config.get("skills", {})
        entries = skills.get("config", []) if isinstance(skills, dict) else []
        if not isinstance(entries, list):
            return set()
        return {
            self.configured_skill_path(entry["path"])
            for entry in entries
            if isinstance(entry, dict)
            and isinstance(entry.get("path"), str)
            and entry.get("enabled") is False
        }

    def run(self) -> list[Check]:
        self.check_config()
        self.check_shell_and_tools()
        self.check_aliyun()
        self.check_brain()
        self.check_jenkins()
        self.check_skills()
        self.check_mcp()
        self.check_external_tools()
        if self.args.codex_doctor:
            self.check_codex_doctor()
        return self.checks

    def check_config(self) -> None:
        if not self.config_path.is_file():
            self.add(
                "config.file",
                "config",
                "FAIL",
                "Codex config.toml is missing",
                remediation=f"Create or restore {self.config_path}",
            )
            return
        mode = self.config_path.stat().st_mode & 0o777
        self.add(
            "config.file",
            "config",
            "PASS" if mode & 0o077 == 0 else "WARN",
            "config.toml exists and is private" if mode & 0o077 == 0 else "config.toml is readable by group or others",
            {"mode": oct(mode)},
            None if mode & 0o077 == 0 else f"chmod 600 {shlex.quote(str(self.config_path))}",
        )
        try:
            self.config = load_toml(self.config_path)
        except (OSError, tomllib.TOMLDecodeError) as exc:
            self.add("config.parse", "config", "FAIL", "config.toml does not parse", {"error": str(exc)})
            return
        self.add("config.parse", "config", "PASS", "config.toml parses as TOML")

        policy = self.config.get("shell_environment_policy", {})
        if isinstance(policy, dict):
            configured_path = policy.get("set", {}).get("PATH") if isinstance(policy.get("set", {}), dict) else None
            if isinstance(configured_path, str) and configured_path:
                self.effective_path = os.path.expandvars(os.path.expanduser(configured_path))
        required = ["model", "approval_policy", "sandbox_mode", "shell_environment_policy"]
        missing = [key for key in required if key not in self.config]
        provider = self.config.get("model_provider")
        providers = self.config.get("model_providers", {})
        provider_missing = bool(provider and (not isinstance(providers, dict) or provider not in providers))
        status = "FAIL" if missing or provider_missing else "PASS"
        details: dict[str, Any] = {"required_keys_present": len(required) - len(missing)}
        if missing:
            details["missing"] = missing
        if provider_missing:
            details["missing_provider_table"] = str(provider)
        self.add("config.contract", "config", status, "core configuration contract is complete" if status == "PASS" else "core configuration contract is incomplete", details)

        codex = self.executable("codex")
        if codex:
            strict = run_command([codex, "--strict-config", "--version"], env=self.command_env(), cwd=self.cwd, timeout=15)
            self.add(
                "config.strict_load",
                "config",
                "PASS" if strict.returncode == 0 else "FAIL",
                "Codex strict config load succeeded" if strict.returncode == 0 else "Codex strict config load failed",
                {"error": compact(strict.stderr)} if strict.returncode else {},
            )
            layered = run_command(
                self.app_server_command(codex, strict=True, disable_mcp=True),
                input_text="",
                env=self.command_env(),
                cwd=self.cwd,
                timeout=15,
            )
            self.add(
                "config.layered_strict_load",
                "config",
                "PASS" if layered.returncode == 0 else "WARN",
                "user and workspace config layers pass strict app-server loading" if layered.returncode == 0 else "a workspace config layer contains fields rejected by strict mode",
                {"error": compact(layered.stderr or layered.stdout)} if layered.returncode else {},
                "Remove or update fields rejected by the current Codex version after confirming their replacement." if layered.returncode else None,
            )
        else:
            self.add("config.strict_load", "config", "FAIL", "Codex CLI is unavailable for strict config validation")

        self.check_platform_match()
        self.check_project_trust()
        approval = str(self.config.get("approval_policy", ""))
        sandbox = str(self.config.get("sandbox_mode", ""))
        risky = approval == "never" and sandbox == "danger-full-access"
        self.add(
            "config.security_posture",
            "config",
            "WARN" if risky else "PASS",
            "Codex is explicitly unrestricted and non-interactive" if risky else "approval and sandbox posture is bounded",
            {"approval_policy": approval, "sandbox_mode": sandbox},
            "Keep this combination only on a trusted machine and trusted repositories." if risky else None,
        )

    def check_platform_match(self) -> None:
        system = platform.system().lower()
        active_values: list[tuple[str, str]] = []
        stale_values: list[tuple[str, str]] = []
        policy = self.config.get("shell_environment_policy", {})
        if isinstance(policy, dict):
            path_value = policy.get("set", {}).get("PATH") if isinstance(policy.get("set", {}), dict) else None
            if isinstance(path_value, str):
                active_values.append(("shell PATH", path_value))
        for key in ("notify", "log_dir"):
            value = self.config.get(key)
            values = value if isinstance(value, list) else [value]
            for item in values:
                if isinstance(item, str):
                    active_values.append((key, item))
        servers = self.config.get("mcp_servers", {})
        if isinstance(servers, dict):
            for name, server in servers.items():
                if not isinstance(server, dict) or server.get("enabled") is False:
                    continue
                for key in ("command", "cwd"):
                    if isinstance(server.get(key), str):
                        active_values.append((f"mcp.{name}.{key}", server[key]))
        projects = self.config.get("projects", {})
        if isinstance(projects, dict):
            stale_values.extend(("project", key) for key in projects if isinstance(key, str))

        def mismatch(value: str) -> bool:
            if system == "darwin":
                return value.startswith("/home/")
            if system == "linux":
                return value.startswith("/Users/") or value.startswith("/Applications/") or "/Applications/" in value
            return False

        active = [label for label, value in active_values if mismatch(value)]
        stale = [label for label, value in stale_values if mismatch(value)]
        status = "FAIL" if active else ("WARN" if stale else "PASS")
        details: dict[str, Any] = {"platform": system}
        if active:
            details["active_mismatches"] = active[:8]
        if stale:
            details["stale_project_entries"] = len(stale)
        self.add(
            "config.platform_match",
            "config",
            status,
            "configuration matches the current OS" if status == "PASS" else "configuration contains paths for another OS",
            details,
        )

    def check_project_trust(self) -> None:
        projects = self.config.get("projects", {})
        matches: list[tuple[int, str]] = []
        if isinstance(projects, dict):
            for raw, cfg in projects.items():
                if not isinstance(raw, str) or not isinstance(cfg, dict):
                    continue
                path = Path(raw).expanduser().resolve(strict=False)
                if self.cwd == path or is_relative_to(self.cwd, path):
                    matches.append((len(path.parts), str(cfg.get("trust_level", "unset"))))
        if matches:
            _, trust = max(matches)
            self.add("config.project_trust", "config", "PASS", "working directory has a matching project trust rule", {"trust_level": trust})
        else:
            self.add(
                "config.project_trust",
                "config",
                "WARN",
                "working directory has no matching project trust rule",
                remediation="Add an explicit [projects.<path>] trust_level entry if this directory should be trusted.",
            )

    def check_shell_and_tools(self) -> None:
        required = {
            "git": ["--version"],
            "codex": ["--version"],
            "brain": ["--version"],
            "glab": ["--version"],
            "plane-cli": ["help"],
            "node": ["--version"],
            "npx": ["--version"],
        }
        for name, version_args in required.items():
            runtime = shutil.which(name)
            configured = shutil.which(name, path=self.effective_path)
            if not runtime and not configured:
                self.add(f"tool.{name}", "tools", "FAIL", f"{name} is not resolvable")
                continue
            selected = configured or runtime
            probe = run_command([selected, *version_args], env=self.command_env(), timeout=10)
            if probe.returncode != 0:
                self.add(f"tool.{name}", "tools", "FAIL", f"{name} exists but its smoke test failed", {"error": compact(probe.stderr or probe.stdout)})
                continue
            if runtime and not configured:
                self.add(
                    f"tool.{name}",
                    "tools",
                    "FAIL",
                    f"{name} is visible in the parent shell but missing from Codex child PATH",
                    {"runtime_path": runtime},
                    "Add its containing directory to shell_environment_policy.set.PATH.",
                )
                continue
            resolution_differs = bool(
                runtime
                and configured
                and Path(runtime).resolve() != Path(configured).resolve()
            )
            first_line = (probe.stdout or probe.stderr).splitlines()[0] if (probe.stdout or probe.stderr).splitlines() else "smoke test ok"
            details = {"path": configured or runtime, "version": compact(first_line, 160)}
            if resolution_differs:
                details["parent_path"] = runtime
            self.add(
                f"tool.{name}",
                "tools",
                "PASS",
                f"{name} is executable in the Codex child PATH",
                details,
            )

        shell = os.environ.get("SHELL") or shutil.which("zsh") or shutil.which("bash")
        if not shell or not Path(shell).exists():
            self.add("shell.login", "shell", "FAIL", "login shell is unavailable")
            return
        names = [*required, "aliyun"]
        script = "; ".join(f"printf '{name}='; command -v {shlex.quote(name)} || true" for name in names)
        probe = run_command([shell, "-lic", script], timeout=15)
        found = {line.split("=", 1)[0] for line in probe.stdout.splitlines() if "=" in line and line.split("=", 1)[1].strip()}
        missing = sorted(set(names) - found)
        self.add(
            "shell.login",
            "shell",
            "PASS" if probe.returncode == 0 and not missing else "WARN",
            "login shell resolves all required tools" if not missing else "login shell is missing required tools",
            {"shell": shell, "missing": missing},
            "Fix shell startup ordering so managed PATH changes do not overwrite tool directories." if missing else None,
        )

        path_entries = [Path(entry).expanduser() for entry in self.effective_path.split(os.pathsep) if entry]
        missing_entries = [str(path) for path in path_entries if not path.is_dir()]
        self.add(
            "shell.configured_path",
            "shell",
            "WARN" if missing_entries else "PASS",
            "configured PATH entries exist" if not missing_entries else "configured PATH contains missing directories",
            {"entries": len(path_entries), "missing": missing_entries[:8]},
        )

    def check_aliyun(self) -> None:
        runtime = shutil.which("aliyun")
        configured = shutil.which("aliyun", path=self.effective_path)
        selected = configured or runtime
        if not selected:
            self.add("aliyun.cli", "aliyun", "FAIL", "Aliyun CLI is not resolvable")
            self.add("aliyun.config", "aliyun", "UNKNOWN", "Aliyun configuration cannot be assessed without the CLI")
            self.add("aliyun.api", "aliyun", "UNKNOWN", "Aliyun API was not queried")
            return
        version = run_command([selected, "version"], env=self.command_env(), timeout=10)
        if version.returncode != 0:
            cli_status = "FAIL"
            cli_summary = "Aliyun CLI exists but its version probe failed"
            cli_details: dict[str, Any] = {"error_class": classify_aliyun_error(version)}
        elif runtime and not configured:
            cli_status = "FAIL"
            cli_summary = "Aliyun CLI is visible in the parent shell but missing from Codex child PATH"
            cli_details = {"parent_path": runtime}
        else:
            first_line = (version.stdout or version.stderr).splitlines()
            cli_status = "PASS"
            cli_summary = "Aliyun CLI is executable in the Codex child PATH"
            cli_details = {
                "path": configured or runtime,
                "version": compact(first_line[0], 80) if first_line else "version probe succeeded",
            }
        self.add(
            "aliyun.cli",
            "aliyun",
            cli_status,
            cli_summary,
            cli_details,
            "Add the Aliyun CLI directory to shell_environment_policy.set.PATH." if runtime and not configured else None,
        )

        config_path = self.home / ".aliyun" / "config.json"
        state = inspect_aliyun_config(config_path, dict(os.environ))
        complete = state.get("credentials_complete") is True
        private = state.get("file_private") is True or state.get("source") == "environment"
        if not complete:
            config_status = "FAIL"
            config_summary = "Aliyun credential configuration is missing or incomplete"
        elif not private:
            config_status = "WARN"
            config_summary = "Aliyun credential configuration is complete but its file permissions are broad"
        else:
            config_status = "PASS"
            config_summary = "Aliyun credential configuration is complete and private"
        self.add(
            "aliyun.config",
            "aliyun",
            config_status,
            config_summary,
            state,
            (
                "Configure a supported Aliyun CLI profile or complete the supported environment credential contract."
                if not complete
                else "Restrict the Aliyun CLI config file to owner-only access."
                if not private
                else None
            ),
        )

        if not self.args.network:
            self.add(
                "aliyun.api",
                "aliyun",
                "UNKNOWN",
                "Aliyun STS identity was not queried",
                remediation="Rerun with --network or --all for a read-only STS GetCallerIdentity probe.",
            )
            return
        if version.returncode != 0 or not complete:
            self.add(
                "aliyun.api",
                "aliyun",
                "FAIL",
                "Aliyun STS probe cannot run with the available CLI and credential configuration",
            )
            return
        identity = run_command(
            [selected, "sts", "GetCallerIdentity"],
            env=self.command_env(),
            cwd=self.cwd,
            timeout=20,
        )
        self.add(
            "aliyun.api",
            "aliyun",
            "PASS" if identity.returncode == 0 else "FAIL",
            "Aliyun STS authentication succeeded" if identity.returncode == 0 else "Aliyun STS authentication failed",
            {"duration_ms": identity.duration_ms}
            if identity.returncode == 0
            else {"error_class": classify_aliyun_error(identity), "duration_ms": identity.duration_ms},
        )

    def check_brain(self) -> None:
        brain = self.executable("brain")
        if not brain:
            self.add("brain.cli", "brain", "FAIL", "Brain CLI is unavailable")
            self.add("brain.tools.inventory", "brain", "FAIL", "Brain tools inventory is unavailable")
            self.add("brain.tools.integrity", "brain", "UNKNOWN", "Brain tools integrity could not be checked")
            self.add("brain.tools.dependencies", "brain", "UNKNOWN", "Brain tool dependencies could not be checked")
            return
        brief = run_command([brain, "brief", "--limit", "1"], env=self.command_env(), cwd=self.cwd, timeout=15)
        self.add(
            "brain.cli",
            "brain",
            "PASS" if brief.returncode == 0 else "FAIL",
            "Brain CLI can read the configured knowledge repository" if brief.returncode == 0 else "Brain CLI cannot read the configured knowledge repository",
            {"error": compact(brief.stderr)} if brief.returncode else {},
        )

        user_hooks = hook_commands(self.config, "UserPromptSubmit")
        stop_hooks = hook_commands(self.config, "Stop")
        user_ok = any("brain hook user-prompt-submit" in command for command in user_hooks)
        stop_ok = any("brain sync" in command and "--background" in command for command in stop_hooks) or any("brain hook stop" in command for command in stop_hooks)
        disabled = []
        state = self.config.get("hooks", {}).get("state", {}) if isinstance(self.config.get("hooks", {}), dict) else {}
        if isinstance(state, dict):
            config_prefix = f"{self.config_path}:"
            disabled = [
                key
                for key, value in state.items()
                if key.startswith(config_prefix)
                and (key.endswith(":stop:0:0") or key.endswith(":user_prompt_submit:0:0"))
                and isinstance(value, dict)
                and value.get("enabled") is False
            ]
        hook_status = "PASS" if user_ok and stop_ok and not disabled else "FAIL"
        self.add(
            "brain.hooks.config",
            "brain",
            hook_status,
            "Brain query-start and stop-sync hooks are configured" if hook_status == "PASS" else "Brain hook configuration is incomplete or disabled",
            {"query_start": user_ok, "stop_sync": stop_ok, "disabled_state_entries": len(disabled)},
            "Run `brain install codex --update` only after reviewing the dry run." if hook_status == "FAIL" else None,
        )
        payload = json.dumps({"prompt": "codex env doctor probe"}) + "\n"
        hook_probe = run_command([brain, "--json", "hook", "user-prompt-submit"], input_text=payload, env=self.command_env(), timeout=10)
        valid_hook = False
        if hook_probe.returncode == 0:
            try:
                response = json.loads(hook_probe.stdout)
                valid_hook = bool(response.get("hookSpecificOutput", {}).get("additionalContext"))
            except json.JSONDecodeError:
                valid_hook = False
        self.add(
            "brain.hooks.runtime",
            "brain",
            "PASS" if valid_hook else "FAIL",
            "Brain UserPromptSubmit hook returns Codex context" if valid_hook else "Brain UserPromptSubmit hook probe failed",
            {"error": compact(hook_probe.stderr or hook_probe.stdout)} if not valid_hook else {},
        )
        self.check_brain_tools(brain)
        self.check_brain_repo()

    def check_brain_tools(self, brain: str) -> None:
        inventory = run_command([brain, "tools", "list"], env=self.command_env(), cwd=self.cwd, timeout=15)
        root = self.brain_root()
        tools_dir = root / "tools" if root else None
        entries = (
            sorted(
                path
                for path in tools_dir.iterdir()
                if path.is_file() and path.suffix in {".py", ".sh", ".bash"}
            )
            if tools_dir and tools_dir.is_dir()
            else []
        )
        inventory_ok = inventory.returncode == 0 and bool(inventory.stdout.strip()) and bool(entries)
        self.add(
            "brain.tools.inventory",
            "brain",
            "PASS" if inventory_ok else "FAIL",
            "Brain tools inventory is readable" if inventory_ok else "Brain tools inventory is unavailable or empty",
            {"entrypoints": len(entries)},
        )
        if not tools_dir or not tools_dir.is_dir():
            self.add("brain.tools.integrity", "brain", "UNKNOWN", "Brain tools directory could not be resolved safely")
            self.add("brain.tools.dependencies", "brain", "UNKNOWN", "Brain tool dependencies could not be checked")
            return

        libraries = sorted(
            path
            for path in (tools_dir / "_lib").rglob("*")
            if path.is_file()
            and path.suffix in {".py", ".sh", ".bash"}
            and "__pycache__" not in path.parts
        ) if (tools_dir / "_lib").is_dir() else []
        checked_files = [*entries, *libraries]
        unreadable: list[str] = []
        missing_shebang: list[str] = []
        syntax_errors: list[str] = []
        non_executable: list[str] = []
        for path in checked_files:
            label = str(path.relative_to(tools_dir))
            if not os.access(path, os.R_OK):
                unreadable.append(label)
                continue
            try:
                first_line = path.read_text(encoding="utf-8").splitlines()[0]
            except (OSError, UnicodeError):
                unreadable.append(label)
                continue
            except IndexError:
                first_line = ""
            if path in entries and not first_line.startswith("#!"):
                missing_shebang.append(label)
            syntax_error = validate_script_syntax(path)
            if syntax_error:
                syntax_errors.append(label)
            if path in entries and not os.access(path, os.X_OK):
                non_executable.append(label)
        integrity_failed = bool(unreadable or missing_shebang or syntax_errors)
        integrity_status = "FAIL" if integrity_failed else ("WARN" if non_executable else "PASS")
        self.add(
            "brain.tools.integrity",
            "brain",
            integrity_status,
            (
                "Brain tool entrypoints and local libraries are syntactically valid"
                if integrity_status == "PASS"
                else "Brain tools contain integrity or executable-bit findings"
            ),
            {
                "entrypoints": len(entries),
                "local_libraries": len(libraries),
                "unreadable": unreadable[:12],
                "missing_shebang": missing_shebang[:12],
                "syntax_errors": syntax_errors[:12],
                "non_executable": non_executable[:12],
            },
        )

        missing_interpreters: set[str] = set()
        missing_modules: set[str] = set()
        missing_local_refs: set[str] = set()
        local_module_names = {
            path.stem
            for path in [*entries, *libraries]
            if path.suffix == ".py"
        }
        for path in checked_files:
            try:
                text = path.read_text(encoding="utf-8")
            except (OSError, UnicodeError):
                continue
            first_line = text.splitlines()[0] if text.splitlines() else ""
            if first_line.startswith("#!"):
                try:
                    shebang = shlex.split(first_line[2:])
                except ValueError:
                    shebang = []
                interpreter = shebang[1] if len(shebang) > 1 and Path(shebang[0]).name == "env" else (shebang[0] if shebang else "")
                if interpreter and not self.executable(interpreter):
                    missing_interpreters.add(Path(interpreter).name)
            if path.suffix == ".py":
                try:
                    tree = ast.parse(text)
                except SyntaxError:
                    continue
                modules: set[str] = set()
                for node in ast.walk(tree):
                    if isinstance(node, ast.Import):
                        modules.update(alias.name.split(".", 1)[0] for alias in node.names)
                    elif isinstance(node, ast.ImportFrom) and node.module:
                        modules.add(node.module.split(".", 1)[0])
                for module in modules:
                    if module in {"__future__", *sys.stdlib_module_names} or module in local_module_names:
                        continue
                    try:
                        available = importlib.util.find_spec(module) is not None
                    except (ImportError, ModuleNotFoundError, ValueError):
                        available = False
                    if not available:
                        missing_modules.add(module)
            else:
                for match in re.finditer(r"_lib/([A-Za-z0-9_.-]+\.(?:sh|py))", text):
                    relative = Path("_lib") / match.group(1)
                    if not (tools_dir / relative).is_file():
                        missing_local_refs.add(str(relative))
        dependency_failed = bool(missing_interpreters or missing_modules or missing_local_refs)
        self.add(
            "brain.tools.dependencies",
            "brain",
            "FAIL" if dependency_failed else "PASS",
            "Brain tool static dependencies are resolvable" if not dependency_failed else "Some Brain tool static dependencies are unavailable",
            {
                "missing_interpreters": sorted(missing_interpreters),
                "missing_python_modules": sorted(missing_modules),
                "missing_local_references": sorted(missing_local_refs),
            },
        )

    def brain_root(self) -> Path | None:
        path = Path(os.environ.get("XDG_CONFIG_HOME", self.home / ".config")) / "brain" / "config.toml"
        try:
            data = load_toml(path)
            default = data.get("default")
            brains = data.get("brains", {})
            if isinstance(default, str) and isinstance(brains, dict):
                entry = brains.get(default, {})
                if isinstance(entry, dict) and isinstance(entry.get("path"), str):
                    root = Path(entry["path"]).expanduser()
                    return root if root.is_dir() else None
        except (OSError, tomllib.TOMLDecodeError):
            return None
        return None

    def check_brain_repo(self) -> None:
        root = self.brain_root()
        git = self.executable("git")
        if not root or not git:
            self.add("brain.repo.local", "brain", "UNKNOWN", "Brain Git repository path could not be resolved safely")
            return
        status = run_command([git, "status", "--porcelain=v2", "--branch"], cwd=root, timeout=10)
        if status.returncode != 0:
            self.add("brain.repo.local", "brain", "FAIL", "Brain repository status failed", {"error": compact(status.stderr)})
            return
        lines = status.stdout.splitlines()
        dirty = sum(1 for line in lines if not line.startswith("#"))
        ab_line = next((line for line in lines if line.startswith("# branch.ab ")), "")
        match = re.search(r"\+(\d+)\s+-(\d+)", ab_line)
        ahead, behind = (int(match.group(1)), int(match.group(2))) if match else (0, 0)
        local_status = "PASS" if not dirty and ahead == 0 and behind == 0 else "WARN"
        self.add(
            "brain.repo.local",
            "brain",
            local_status,
            "Brain repository is clean against its local upstream snapshot" if local_status == "PASS" else "Brain repository has local changes or divergence",
            {"dirty_paths": dirty, "ahead": ahead, "behind": behind},
        )
        if not self.args.network:
            self.add(
                "brain.repo.remote",
                "brain",
                "UNKNOWN",
                "Brain remote SHA was not queried",
                remediation="Rerun with --network to distinguish a clean local snapshot from current remote truth.",
            )
            return
        upstream = run_command([git, "rev-parse", "--abbrev-ref", "@{upstream}"], cwd=root, timeout=5)
        local = run_command([git, "rev-parse", "HEAD"], cwd=root, timeout=5)
        tracking = run_command([git, "rev-parse", "@{upstream}"], cwd=root, timeout=5)
        if upstream.returncode or local.returncode or tracking.returncode or "/" not in upstream.stdout.strip():
            self.add("brain.repo.remote", "brain", "UNKNOWN", "Brain upstream branch is unavailable")
            return
        remote, branch = upstream.stdout.strip().split("/", 1)
        env = os.environ.copy()
        env["GIT_TERMINAL_PROMPT"] = "0"
        ls_remote = run_command([git, "ls-remote", "--exit-code", remote, f"refs/heads/{branch}"], cwd=root, env=env, timeout=20)
        if ls_remote.returncode != 0 or not ls_remote.stdout.strip():
            self.add("brain.repo.remote", "brain", "FAIL", "Brain remote branch could not be queried", {"error": compact(ls_remote.stderr)})
            return
        remote_sha = ls_remote.stdout.split()[0]
        local_sha = local.stdout.strip()
        tracking_sha = tracking.stdout.strip()
        if remote_sha == local_sha:
            status_name, summary = "PASS", "Brain HEAD matches the current remote SHA"
        elif remote_sha == tracking_sha:
            status_name, summary = "WARN", "Brain has local commits not present on the remote"
        elif local_sha == tracking_sha:
            status_name, summary = "FAIL", "Brain remote advanced beyond the local checkout"
        else:
            status_name, summary = "FAIL", "Brain local and remote histories differ from the tracking snapshot"
        self.add("brain.repo.remote", "brain", status_name, summary)

    def jenkins_helper(self) -> Path | None:
        candidates: list[Path] = []
        workspace = os.environ.get("SKYWORK_AGENT_ROOT")
        if workspace:
            candidates.append(Path(workspace).expanduser() / "brain" / "tools" / "jenkins.sh")
        candidates.extend(parent / "brain" / "tools" / "jenkins.sh" for parent in (self.cwd, *self.cwd.parents))
        brain_root = self.brain_root()
        if brain_root:
            candidates.append(brain_root / "tools" / "jenkins.sh")
        seen: set[str] = set()
        for candidate in candidates:
            key = str(candidate.resolve(strict=False))
            if key in seen:
                continue
            seen.add(key)
            if candidate.is_file():
                return candidate.expanduser().absolute()
        return None

    def check_jenkins(self) -> None:
        helper = self.jenkins_helper()
        if not helper:
            self.add(
                "jenkins.tool",
                "jenkins",
                "FAIL",
                "brain/tools/jenkins.sh could not be located",
                remediation="Run from the Skywork workspace or set SKYWORK_AGENT_ROOT to the workspace root.",
            )
            self.add("jenkins.env.file", "jenkins", "FAIL", "Jenkins credential source could not be located")
            self.add("jenkins.api", "jenkins", "UNKNOWN", "Jenkins API probe is unavailable without the helper contract")
            return

        bash = self.executable("bash")
        syntax = run_command([bash or "/bin/bash", "-n", str(helper)], timeout=5)
        dependencies = [name for name in ("bash", "curl", "python3") if not self.executable(name)]
        try:
            helper_text = helper.read_text(encoding="utf-8")
        except (OSError, UnicodeError):
            helper_text = ""
        contract_ok = all(name in helper_text for name in JENKINS_ENV_KEYS) and "/api/json" in helper_text
        executable = os.access(helper, os.X_OK)
        tool_status = "FAIL" if syntax.returncode or dependencies or not contract_ok else ("PASS" if executable else "WARN")
        self.add(
            "jenkins.tool",
            "jenkins",
            tool_status,
            "Jenkins helper and local dependencies are usable" if tool_status == "PASS" else "Jenkins helper has a local availability problem",
            {
                "helper": str(helper),
                "executable": executable,
                "syntax_ok": syntax.returncode == 0,
                "contract_ok": contract_ok,
                "missing_dependencies": dependencies,
            },
            "Restore the helper, its executable bit, or its required local commands before using Jenkins." if tool_status != "PASS" else None,
        )

        workspace = os.environ.get("SKYWORK_AGENT_ROOT")
        env_file = Path(workspace).expanduser() / ".env" if workspace else helper.parents[2] / ".env"
        file_values, invalid = load_env_assignments(env_file, JENKINS_ENV_KEYS) if env_file.is_file() else ({}, [])
        present = sorted(name for name in JENKINS_ENV_KEYS if file_values.get(name))
        empty = sorted(name for name in JENKINS_ENV_KEYS if name in file_values and not file_values[name])
        missing = sorted(name for name in JENKINS_ENV_KEYS if name not in file_values)
        url_ok = valid_jenkins_url(file_values.get("JENKINS_URL"))
        mode = env_file.stat().st_mode & 0o777 if env_file.is_file() else None
        private = mode is not None and mode & 0o077 == 0
        if not env_file.is_file() or missing or empty or invalid or not url_ok:
            env_status = "FAIL"
            env_summary = "Jenkins workspace credential configuration is missing or invalid"
        elif not private:
            env_status = "WARN"
            env_summary = "Jenkins credential configuration is complete but its file permissions are broad"
        else:
            env_status = "PASS"
            env_summary = "Jenkins workspace credential configuration is complete and private"
        self.add(
            "jenkins.env.file",
            "jenkins",
            env_status,
            env_summary,
            {
                "source": str(env_file),
                "present": present,
                "missing": missing,
                "empty": empty,
                "invalid_assignments": invalid,
                "url_valid": url_ok,
                "mode": oct(mode) if mode is not None else None,
            },
            (
                f"Restrict the credential file with `chmod 600 {shlex.quote(str(env_file))}` after confirming all required names are set."
                if env_status == "WARN"
                else "Define JENKINS_URL, JENKINS_USER, and JENKINS_TOKEN in the helper's private workspace .env file."
                if env_status == "FAIL"
                else None
            ),
        )

        codex_present = sorted(name for name in JENKINS_ENV_KEYS if os.environ.get(name))
        codex_missing = sorted(set(JENKINS_ENV_KEYS) - set(codex_present))
        policy = self.config.get("shell_environment_policy", {})
        policy = policy if isinstance(policy, dict) else {}
        policy_set = policy.get("set", {})
        policy_set = policy_set if isinstance(policy_set, dict) else {}
        explicitly_set = sorted(name for name in JENKINS_ENV_KEYS if name in policy_set)
        self.add(
            "jenkins.env.codex",
            "jenkins",
            "PASS" if not codex_missing else "WARN",
            "Jenkins variables are available to the current Codex process" if not codex_missing else "Jenkins variables are not directly inherited by the current Codex process",
            {
                "present": codex_present,
                "missing": codex_missing,
                "policy_inherit": policy.get("inherit", "unset"),
                "explicitly_set_names": explicitly_set,
                "helper_has_private_source": env_status in {"PASS", "WARN"},
            },
            "Use a private credential source; do not add Jenkins secrets directly to config.toml. The validated helper can source the workspace .env file." if codex_missing else None,
        )

        shell = os.environ.get("SHELL") or self.executable("zsh") or self.executable("bash")
        if shell and Path(shell).is_file():
            statements = [
                f'''if [ -n "${{{name}:-}}" ]; then printf '{name}=1\\n'; else printf '{name}=0\\n'; fi'''
                for name in JENKINS_ENV_KEYS
            ]
            login = run_command([shell, "-lic", "\n".join(statements)], timeout=15)
            login_present = sorted(
                line.split("=", 1)[0]
                for line in login.stdout.splitlines()
                if line in {f"{name}=1" for name in JENKINS_ENV_KEYS}
            )
            login_missing = sorted(set(JENKINS_ENV_KEYS) - set(login_present))
            self.add(
                "jenkins.env.login_shell",
                "jenkins",
                "PASS" if login.returncode == 0 and not login_missing else "WARN",
                "Login shell exports all Jenkins variables" if not login_missing else "Login shell does not export all Jenkins variables",
                {"shell": shell, "present": login_present, "missing": login_missing},
                "This is optional when the Jenkins helper's private workspace .env source is healthy." if login_missing else None,
            )
        else:
            self.add("jenkins.env.login_shell", "jenkins", "UNKNOWN", "Login shell is unavailable for Jenkins variable checks")

        if not self.args.network:
            self.add(
                "jenkins.api",
                "jenkins",
                "UNKNOWN",
                "Jenkins credentials and API were not queried",
                remediation="Rerun with --network or --all for a read-only authenticated API probe.",
            )
            return
        effective_credentials = {name: os.environ.get(name, "") for name in JENKINS_ENV_KEYS}
        effective_credentials.update(file_values)
        unavailable = sorted(name for name in JENKINS_ENV_KEYS if not effective_credentials.get(name))
        if unavailable or not valid_jenkins_url(effective_credentials.get("JENKINS_URL")):
            self.add(
                "jenkins.api",
                "jenkins",
                "FAIL",
                "Jenkins API probe cannot run with the available credential configuration",
                {"missing": unavailable, "url_valid": valid_jenkins_url(effective_credentials.get("JENKINS_URL"))},
            )
            return
        result = probe_jenkins_api(effective_credentials)
        self.add("jenkins.api", "jenkins", result["status"], result["summary"], result.get("details", {}))

    def check_skills(self) -> None:
        roots = skill_roots(self.cwd, self.home)
        disabled_paths = self.disabled_skill_paths()
        records: list[SkillRecord] = []
        invalid: list[str] = []
        broken_links: list[str] = []
        misplaced: list[str] = []
        missing_refs: list[str] = []
        script_errors: list[str] = []
        oversized: list[str] = []
        noncanonical: list[str] = []
        scanned_roots = 0
        for scope, root in roots:
            if not root.exists():
                continue
            scanned_roots += 1
            try:
                children = sorted(root.iterdir(), key=lambda path: path.name)
            except OSError as exc:
                invalid.append(f"{scope}:{root.name}: unreadable ({exc})")
                continue
            for child in children:
                if child.name.startswith("."):
                    continue
                if child.is_symlink() and not child.exists():
                    broken_links.append(f"{scope}:{child.name}")
                    continue
                if not child.is_dir():
                    misplaced.append(f"{scope}:{child.name}")
                    continue
                skill_file = child / "SKILL.md"
                if not skill_file.is_file():
                    misplaced.append(f"{scope}:{child.name}")
                    continue
                metadata, error = parse_frontmatter(skill_file)
                name = metadata.get("name", "").strip()
                description = metadata.get("description", "").strip()
                if error or not name or not description:
                    reason = error or "missing name or description"
                    invalid.append(f"{scope}:{child.name}: {reason}")
                    continue
                line_count = len(skill_file.read_text(encoding="utf-8").splitlines())
                enabled = skill_file.resolve(strict=False) not in disabled_paths
                record = SkillRecord(name, description, child, skill_file, scope, line_count, enabled)
                records.append(record)
                if name != child.name or not SKILL_NAME.fullmatch(name):
                    noncanonical.append(f"{scope}:{child.name}->{name}")
                if enabled and line_count > 500:
                    oversized.append(f"{scope}:{child.name} ({line_count} lines)")
                try:
                    text = skill_file.read_text(encoding="utf-8")
                except (OSError, UnicodeError):
                    text = ""
                for raw_link in MARKDOWN_LINK.findall(text):
                    link = raw_link.split("#", 1)[0].strip().strip("<>")
                    resource_prefixes = ("./", "../", "references/", "scripts/", "assets/", "agents/")
                    if (
                        not link
                        or "://" in link
                        or link.startswith(("#", "/"))
                        or not link.startswith(resource_prefixes)
                    ):
                        continue
                    target = (child / link).resolve(strict=False)
                    if not target.exists():
                        missing_refs.append(f"{scope}:{child.name}:{link}")
                scripts = child / "scripts"
                if scripts.is_dir():
                    for script in scripts.rglob("*"):
                        if script.is_file() and script.suffix in {".py", ".sh", ".bash"}:
                            syntax_error = validate_script_syntax(script)
                            if syntax_error:
                                script_errors.append(f"{scope}:{child.name}:{script.name}: {syntax_error}")

        self.add(
            "skills.discovery_roots",
            "skills",
            "PASS" if scanned_roots else "FAIL",
            "Codex skill discovery roots are readable" if scanned_roots else "no Codex skill discovery root is readable",
            {"roots_scanned": scanned_roots, "valid_skills": len(records)},
        )
        integrity_failures = len(invalid) + len(broken_links) + len(script_errors)
        integrity_status = "FAIL" if integrity_failures else ("WARN" if missing_refs or noncanonical else "PASS")
        self.add(
            "skills.integrity",
            "skills",
            integrity_status,
            "skill entrypoints and bundled scripts are valid" if integrity_status == "PASS" else "some skills are invalid or non-canonical",
            {
                "invalid": invalid[:10],
                "broken_symlinks": broken_links[:10],
                "missing_references": missing_refs[:10],
                "script_errors": script_errors[:10],
                "name_mismatches": noncanonical[:10],
            },
        )
        self.add(
            "skills.root_hygiene",
            "skills",
            "WARN" if misplaced else "PASS",
            "skill roots contain only skill directories" if not misplaced else "skill roots contain non-skill entries",
            {"non_skill_entries": misplaced[:20], "count": len(misplaced)},
            "Move shared references and assets inside their owning skill directory." if misplaced else None,
        )

        by_name: dict[str, list[SkillRecord]] = defaultdict(list)
        enabled_records = [record for record in records if record.enabled]
        for record in enabled_records:
            by_name[record.name].append(record)
        duplicates = {name: [record.scope for record in items] for name, items in by_name.items() if len(items) > 1}
        self.add(
            "skills.duplicates",
            "skills",
            "WARN" if duplicates else "PASS",
            "skill names are unambiguous" if not duplicates else "duplicate skill names may both appear in selectors",
            {"duplicates": duplicates},
        )
        self.add(
            "skills.entrypoint_size",
            "skills",
            "WARN" if oversized else "PASS",
            "enabled skill entrypoints follow progressive-disclosure guidance" if not oversized else "some enabled skill entrypoints exceed 500 lines",
            {"oversized_entrypoints": oversized[:10]},
            "Move detailed command references and long runbooks into references/." if oversized else None,
        )
        self.check_skill_config(records)
        self.check_skill_lock()
        runtime = self.check_skill_runtime(enabled_records)
        self.check_skill_metadata(enabled_records, runtime)

    def check_skill_config(self, records: list[SkillRecord]) -> None:
        skills = self.config.get("skills", {})
        entries = skills.get("config", []) if isinstance(skills, dict) else []
        if not isinstance(entries, list):
            self.add("skills.config", "skills", "FAIL", "[[skills.config]] has an invalid shape")
            return
        missing: list[str] = []
        disabled = 0
        for entry in entries:
            if not isinstance(entry, dict) or not isinstance(entry.get("path"), str):
                missing.append("invalid config entry")
                continue
            path = self.configured_skill_path(entry["path"])
            if not path.is_file():
                missing.append(path.name or "missing path")
            if entry.get("enabled") is False:
                disabled += 1
        self.add(
            "skills.config",
            "skills",
            "WARN" if missing else "PASS",
            "configured skill overrides point to files" if not missing else "configured skill overrides contain missing paths",
            {"overrides": len(entries), "disabled": disabled, "missing": missing[:10]},
        )

    def check_skill_metadata(
        self,
        records: list[SkillRecord],
        runtime: dict[str, Any] | None,
    ) -> None:
        metadata_chars = sum(
            len(record.name) + len(record.description) + len(str(record.skill_file))
            for record in records
        )
        heuristic_pressure = metadata_chars > 8000 or len(records) > 80
        if runtime is None:
            status = "UNKNOWN" if heuristic_pressure else "PASS"
            summary = (
                "runtime inventory is unavailable, so heuristic metadata pressure is unconfirmed"
                if heuristic_pressure
                else "enabled skill metadata is within the conservative fallback budget"
            )
        else:
            status = "PASS" if runtime["complete"] else "WARN"
            summary = (
                "fresh Codex loading exposed every enabled local skill"
                if runtime["complete"]
                else "fresh Codex loading omitted or rejected enabled local skills"
            )
        details: dict[str, Any] = {
            "enabled_skills_on_disk": len(records),
            "approx_metadata_chars": metadata_chars,
            "heuristic_pressure": heuristic_pressure,
        }
        if runtime is not None:
            details.update(
                {
                    "runtime_skills": runtime["runtime_skills"],
                    "runtime_enabled_skills": runtime["enabled_skills"],
                    "load_errors": runtime["load_errors"],
                    "missing_names": runtime["missing_names"],
                }
            )
        self.add("skills.metadata_budget", "skills", status, summary, details)

    def check_skill_lock(self) -> None:
        lock = self.home / ".agents" / ".skill-lock.json"
        if not lock.exists():
            self.add("skills.lock", "skills", "UNKNOWN", "no user skill lock file is present")
            return
        try:
            data = json.loads(lock.read_text(encoding="utf-8"))
            entries = data.get("skills", {})
            if not isinstance(entries, dict):
                raise ValueError("skills must be an object")
        except (OSError, json.JSONDecodeError, ValueError) as exc:
            self.add("skills.lock", "skills", "FAIL", "skill lock JSON is invalid", {"error": str(exc)})
            return
        root = self.home / ".agents" / "skills"
        missing = [name for name in entries if not (root / name / "SKILL.md").is_file()]
        self.add(
            "skills.lock",
            "skills",
            "WARN" if missing else "PASS",
            "skill lock entries resolve to installed skills" if not missing else "skill lock references missing skills",
            {"locked": len(entries), "missing": missing[:15]},
        )

    def check_skill_runtime(self, records: list[SkillRecord]) -> dict[str, Any] | None:
        codex = self.executable("codex")
        if not codex:
            self.add("skills.codex_load", "skills", "UNKNOWN", "Codex app-server is unavailable for skills/list")
            self.add("skills.current_session_exposure", "skills", "UNKNOWN", "the current session skill registry is not available to the standalone doctor")
            return None
        self.add(
            "skills.current_session_exposure",
            "skills",
            "UNKNOWN",
            "fresh Codex loading does not prove the already-running session refreshed its skill list",
            remediation="Compare with `/skills` or start the next task with `$codex-env-doctor`.",
        )
        proc: subprocess.Popen[str] | None = None
        stderr_tail: list[str] = []
        try:
            proc = subprocess.Popen(
                self.app_server_command(codex, disable_mcp=True),
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1,
                env=self.command_env(),
                cwd=str(self.cwd),
                start_new_session=True,
            )
            assert proc.stdin and proc.stdout and proc.stderr
            selector = selectors.DefaultSelector()
            selector.register(proc.stdout, selectors.EVENT_READ, "stdout")
            selector.register(proc.stderr, selectors.EVENT_READ, "stderr")

            def send(message: dict[str, Any]) -> None:
                assert proc and proc.stdin
                proc.stdin.write(json.dumps(message, separators=(",", ":")) + "\n")
                proc.stdin.flush()

            send({
                "id": 1,
                "method": "initialize",
                "params": {
                    "clientInfo": {"name": "codex-env-doctor", "version": "1.0"},
                    "capabilities": {"experimentalApi": True},
                },
            })
            deadline = time.monotonic() + 25
            response: dict[str, Any] | None = None
            while time.monotonic() < deadline:
                if proc.poll() is not None:
                    break
                for key, _ in selector.select(timeout=0.25):
                    line = key.fileobj.readline()
                    if not line:
                        continue
                    if key.data == "stderr":
                        stderr_tail.append(line.strip())
                        stderr_tail[:] = stderr_tail[-12:]
                        continue
                    try:
                        message = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    if message.get("id") == 1:
                        if "error" in message:
                            response = message
                            break
                        send({"method": "initialized"})
                        send({
                            "id": 2,
                            "method": "skills/list",
                            "params": {"cwds": [str(self.cwd)], "forceReload": True},
                        })
                    elif message.get("id") == 2:
                        response = message
                        break
                if response is not None:
                    break
            if not response or "error" in response:
                error = response.get("error") if response else "\n".join(stderr_tail)
                self.add(
                    "skills.codex_load",
                    "skills",
                    "FAIL",
                    "Codex skills/list did not return a usable inventory",
                    {"error": compact(json.dumps(error) if not isinstance(error, str) else error)},
                )
                return None
            entries = response.get("result", {}).get("data", [])
            runtime_skills: list[dict[str, Any]] = []
            errors: list[dict[str, Any]] = []
            for entry in entries if isinstance(entries, list) else []:
                if not isinstance(entry, dict):
                    continue
                runtime_skills.extend(item for item in entry.get("skills", []) if isinstance(item, dict))
                errors.extend(item for item in entry.get("errors", []) if isinstance(item, dict))
            enabled = [item for item in runtime_skills if item.get("enabled") is True]
            doctor_loaded = any(item.get("name") == "codex-env-doctor" for item in enabled)
            disk_counts = Counter(record.name for record in records)
            runtime_counts = Counter(str(item.get("name")) for item in enabled)
            missing = sorted(name for name, count in disk_counts.items() if runtime_counts[name] < count)
            status = "PASS" if doctor_loaded and not errors and not missing else ("WARN" if doctor_loaded else "FAIL")
            self.add(
                "skills.codex_load",
                "skills",
                status,
                "Codex force-reloaded and exposed the valid local skills" if status == "PASS" else "Codex skills/list differs from the filesystem inventory",
                {
                    "runtime_skills": len(runtime_skills),
                    "enabled_skills": len(enabled),
                    "doctor_loaded": doctor_loaded,
                    "load_errors": len(errors),
                    "missing_names": missing[:15],
                },
                "Restart Codex and inspect skills/list errors if a valid local skill remains absent." if status != "PASS" else None,
            )
            return {
                "complete": doctor_loaded and not errors and not missing,
                "runtime_skills": len(runtime_skills),
                "enabled_skills": len(enabled),
                "load_errors": len(errors),
                "missing_names": missing,
            }
        except (OSError, ValueError) as exc:
            self.add("skills.codex_load", "skills", "FAIL", "Codex app-server skill probe failed", {"error": str(exc)})
            return None
        finally:
            if proc and proc.poll() is None:
                try:
                    os.killpg(proc.pid, signal.SIGTERM)
                    proc.wait(timeout=3)
                except (ProcessLookupError, subprocess.TimeoutExpired):
                    try:
                        os.killpg(proc.pid, signal.SIGKILL)
                    except ProcessLookupError:
                        pass

    def check_mcp(self) -> None:
        servers = self.config.get("mcp_servers", {})
        chrome_name = None
        chrome: dict[str, Any] | None = None
        if isinstance(servers, dict):
            for name, cfg in servers.items():
                if "chrome" in name.lower() and "devtools" in name.lower() and isinstance(cfg, dict):
                    chrome_name, chrome = name, cfg
                    break
        if not chrome:
            self.add("mcp.chrome.config", "mcp", "FAIL", "Chrome DevTools MCP is not configured")
            return
        enabled = chrome.get("enabled", True) is not False
        command = chrome.get("command")
        args = chrome.get("args", [])
        command_ok = isinstance(command, str) and bool(self.executable(command) if not os.path.isabs(command) else Path(command).is_file())
        config_status = "PASS" if enabled and command_ok and isinstance(args, list) else "FAIL"
        self.add(
            "mcp.chrome.config",
            "mcp",
            config_status,
            "Chrome DevTools MCP is enabled and its command resolves" if config_status == "PASS" else "Chrome DevTools MCP configuration is unusable",
            {"server": chrome_name, "enabled": enabled, "transport": "stdio"},
        )
        codex = self.executable("codex")
        if codex:
            listed = run_command([codex, "mcp", "list", "--json"], env=self.command_env(), cwd=self.cwd, timeout=20)
            recognized = False
            if listed.returncode == 0:
                try:
                    inventory = json.loads(listed.stdout)
                    recognized = any(item.get("name") == chrome_name and item.get("enabled") is True for item in inventory if isinstance(item, dict))
                except json.JSONDecodeError:
                    recognized = False
            self.add(
                "mcp.chrome.codex_registry",
                "mcp",
                "PASS" if recognized else "FAIL",
                "Codex recognizes Chrome DevTools MCP as enabled" if recognized else "Codex does not expose Chrome DevTools MCP as enabled",
                {"error": compact(listed.stderr or listed.stdout)} if not recognized else {},
            )
        if config_status != "PASS":
            return
        preflight = self.chrome_preflight(chrome)
        self.add(
            "mcp.chrome.process_start",
            "mcp",
            "PASS" if preflight.returncode == 0 else "FAIL",
            "Chrome DevTools MCP package starts" if preflight.returncode == 0 else "Chrome DevTools MCP package fails before protocol initialization",
            {"error": compact(preflight.stderr or preflight.stdout), "duration_ms": preflight.duration_ms} if preflight.returncode else {"duration_ms": preflight.duration_ms},
            "Repair or refresh the configured package/runtime, then rerun --mcp-probe." if preflight.returncode else None,
        )
        self.check_chrome_processes()
        if not self.args.mcp_probe:
            self.add("mcp.chrome.protocol", "mcp", "UNKNOWN", "Chrome DevTools MCP protocol probe was not requested", remediation="Rerun with --mcp-probe.")
            return
        if preflight.returncode != 0:
            self.add("mcp.chrome.protocol", "mcp", "FAIL", "protocol probe skipped because the MCP package cannot start")
            return
        result = self.probe_stdio_mcp(chrome)
        self.add(
            "mcp.chrome.protocol",
            "mcp",
            result["status"],
            result["summary"],
            result.get("details", {}),
            result.get("remediation"),
        )

    def chrome_preflight(self, chrome: dict[str, Any]) -> CommandResult:
        command = str(chrome["command"])
        executable = self.executable(command) or command
        args = [str(arg) for arg in chrome.get("args", [])]
        if Path(executable).name == "npx":
            prefix = [arg for arg in args if arg in {"-y", "--yes"}]
            package = next((arg for arg in args if "chrome-devtools-mcp" in arg), "chrome-devtools-mcp@latest")
            probe_args = [executable, *prefix, package, "--version"]
        else:
            probe_args = [executable, "--version"]
        return run_command(probe_args, env=self.command_env(), cwd=self.cwd, timeout=30)

    def check_chrome_processes(self) -> None:
        ps = run_command(["ps", "-axo", "pgid=,rss=,command="], timeout=5)
        if ps.returncode != 0:
            self.add("mcp.chrome.process_budget", "mcp", "UNKNOWN", "Chrome MCP process inventory is unavailable")
            return
        count = 0
        rss_kib = 0
        instance_groups: set[int] = set()
        for line in ps.stdout.splitlines():
            if "chrome-devtools-mcp" not in line and "chrome-headless-shell" not in line:
                continue
            match = re.match(r"\s*(\d+)\s+(\d+)\s+(.*)$", line)
            if match:
                count += 1
                pgid, rss, command = match.groups()
                rss_kib += int(rss)
                if "telemetry/watchdog" not in command and "chrome-headless-shell" not in command:
                    instance_groups.add(int(pgid))
        instances = len(instance_groups)
        warn = instances > 2 or count > 20 or rss_kib > 1024 * 1024
        self.add(
            "mcp.chrome.process_budget",
            "mcp",
            "WARN" if warn else "PASS",
            "Chrome MCP process footprint is bounded" if not warn else "Chrome MCP process footprint is unusually high",
            {"instances": instances, "processes": count, "rss_mib": round(rss_kib / 1024, 1)},
            "Restart Codex after active tasks finish, or terminate confirmed orphan MCP groups." if warn else None,
        )

    def probe_stdio_mcp(self, chrome: dict[str, Any]) -> dict[str, Any]:
        for attempt in range(1, 3):
            result = self._probe_stdio_mcp_once(chrome)
            result.setdefault("details", {})["attempts"] = attempt
            if result["status"] == "PASS" or result["summary"] != "Chrome DevTools MCP list_pages timed out":
                return result
            time.sleep(0.5)
        return result

    def _probe_stdio_mcp_once(self, chrome: dict[str, Any]) -> dict[str, Any]:
        command = str(chrome["command"])
        executable = self.executable(command) or command
        args = [str(arg) for arg in chrome.get("args", [])]
        probe_log = Path(f"/tmp/codex-env-doctor-mcp-{os.getpid()}-{time.time_ns()}.log")
        if "--no-usage-statistics" not in args:
            args.append("--no-usage-statistics")
        args.extend(["--logFile", str(probe_log)])
        env = self.command_env()
        mcp_env = chrome.get("env", {})
        if isinstance(mcp_env, dict):
            env.update({str(key): str(value) for key, value in mcp_env.items()})
        cwd = Path(str(chrome.get("cwd", self.cwd))).expanduser()
        proc: subprocess.Popen[str] | None = None
        stderr_tail: list[str] = []
        try:
            proc = subprocess.Popen(
                [executable, *args],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1,
                env=env,
                cwd=str(cwd),
                start_new_session=True,
            )
            assert proc.stdin and proc.stdout and proc.stderr
            selector = selectors.DefaultSelector()
            selector.register(proc.stdout, selectors.EVENT_READ, "stdout")
            selector.register(proc.stderr, selectors.EVENT_READ, "stderr")

            def send(message: dict[str, Any]) -> None:
                assert proc and proc.stdin
                proc.stdin.write(json.dumps(message, separators=(",", ":")) + "\n")
                proc.stdin.flush()

            send({
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {
                    "protocolVersion": "2025-06-18",
                    "capabilities": {},
                    "clientInfo": {"name": "codex-env-doctor", "version": "1.0"},
                },
            })
            deadline = time.monotonic() + 30
            initialized = False
            tools: list[dict[str, Any]] = []
            operation: dict[str, Any] | None = None
            while time.monotonic() < deadline:
                if proc.poll() is not None:
                    break
                for key, _ in selector.select(timeout=0.25):
                    line = key.fileobj.readline()
                    if not line:
                        continue
                    if key.data == "stderr":
                        stderr_tail.append(line.strip())
                        stderr_tail[:] = stderr_tail[-12:]
                        continue
                    try:
                        message = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    if message.get("id") == 1:
                        if "error" in message:
                            return {"status": "FAIL", "summary": "MCP initialize returned an error", "details": {"error": compact(json.dumps(message["error"]))}}
                        initialized = True
                        send({"jsonrpc": "2.0", "method": "notifications/initialized", "params": {}})
                        send({"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}})
                    elif message.get("id") == 2:
                        tools = message.get("result", {}).get("tools", [])
                        if not isinstance(tools, list):
                            tools = []
                        names = {item.get("name") for item in tools if isinstance(item, dict)}
                        if "list_pages" not in names:
                            return {"status": "FAIL", "summary": "MCP started but does not expose list_pages", "details": {"tool_count": len(tools)}}
                        send({"jsonrpc": "2.0", "id": 3, "method": "tools/call", "params": {"name": "list_pages", "arguments": {}}})
                    elif message.get("id") == 3:
                        operation = message
                        break
                if operation is not None:
                    break
            if not initialized:
                return {"status": "FAIL", "summary": "Chrome DevTools MCP did not complete initialize", "details": {"error": compact("\n".join(stderr_tail))}}
            if not tools:
                return {"status": "FAIL", "summary": "Chrome DevTools MCP did not return a tool inventory", "details": {"error": compact("\n".join(stderr_tail))}}
            if operation is None:
                return {"status": "FAIL", "summary": "Chrome DevTools MCP list_pages timed out", "details": {"tool_count": len(tools), "error": compact("\n".join(stderr_tail))}}
            if "error" in operation or operation.get("result", {}).get("isError") is True:
                payload = operation.get("error") or operation.get("result")
                return {"status": "FAIL", "summary": "Chrome DevTools MCP protocol works but list_pages failed", "details": {"tool_count": len(tools), "error": compact(json.dumps(payload))}}
            return {"status": "PASS", "summary": "Chrome DevTools MCP initialized, listed tools, and completed list_pages", "details": {"tool_count": len(tools)}}
        except (OSError, ValueError) as exc:
            return {"status": "FAIL", "summary": "Chrome DevTools MCP process could not be probed", "details": {"error": str(exc)}}
        finally:
            if proc and proc.poll() is None:
                try:
                    os.killpg(proc.pid, signal.SIGTERM)
                    proc.wait(timeout=3)
                except (ProcessLookupError, subprocess.TimeoutExpired):
                    try:
                        os.killpg(proc.pid, signal.SIGKILL)
                    except ProcessLookupError:
                        pass
            terminate_tagged_processes(str(probe_log))
            probe_log.unlink(missing_ok=True)

    def check_external_tools(self) -> None:
        plane = self.executable("plane-cli")
        if plane:
            config = run_command([plane, "--output", "json", "config", "show"], env=self.command_env(), timeout=10)
            configured = False
            if config.returncode == 0:
                try:
                    values = json.loads(config.stdout).get("config", {})
                    configured = all(values.get(key) for key in ("base_url", "api_key", "workspace"))
                except json.JSONDecodeError:
                    configured = False
            self.add(
                "plane.config",
                "external",
                "PASS" if configured else "FAIL",
                "Plane CLI has base URL, API key, and workspace configuration" if configured else "Plane CLI configuration is incomplete",
            )
            if self.args.network:
                me = run_command([plane, "--output", "json", "me"], env=self.command_env(), timeout=20)
                active = False
                if me.returncode == 0:
                    try:
                        active = json.loads(me.stdout).get("is_active") is True
                    except json.JSONDecodeError:
                        active = False
                self.add("plane.api", "external", "PASS" if active else "FAIL", "Plane API authentication succeeded" if active else "Plane API authentication failed", {"error": compact(me.stderr or me.stdout)} if not active else {})
            else:
                self.add("plane.api", "external", "UNKNOWN", "Plane API was not queried", remediation="Rerun with --network.")

        glab = self.executable("glab")
        if glab:
            if self.args.network:
                auth = run_command([glab, "auth", "status"], env=self.command_env(), timeout=20)
                self.add("glab.auth", "external", "PASS" if auth.returncode == 0 else "FAIL", "GitLab CLI authentication succeeded" if auth.returncode == 0 else "GitLab CLI authentication failed", {"error": compact(auth.stderr or auth.stdout)} if auth.returncode else {})
            else:
                self.add("glab.auth", "external", "UNKNOWN", "GitLab authentication was not queried", remediation="Rerun with --network.")

    def check_codex_doctor(self) -> None:
        codex = self.executable("codex")
        if not codex:
            return
        result = run_command([codex, "doctor", "--json"], env=self.command_env(), cwd=self.cwd, timeout=90)
        try:
            report = json.loads(result.stdout)
            checks = report.get("checks", {})
        except json.JSONDecodeError:
            self.add("codex.doctor", "codex", "FAIL", "codex doctor did not return JSON", {"error": compact(result.stderr or result.stdout)})
            return
        failures: list[str] = []
        warnings: list[str] = []
        contextual: list[str] = []
        for check_id, item in checks.items() if isinstance(checks, dict) else []:
            status = item.get("status") if isinstance(item, dict) else None
            summary = item.get("summary", "") if isinstance(item, dict) else ""
            if check_id == "terminal.env" and status == "fail" and "TERM=dumb" in summary and not sys.stdout.isatty():
                contextual.append(check_id)
            elif status == "fail":
                failures.append(check_id)
            elif status == "warning":
                warnings.append(check_id)
        status_name = "FAIL" if failures else ("WARN" if warnings or contextual else "PASS")
        self.add(
            "codex.doctor",
            "codex",
            status_name,
            "Codex built-in doctor passed" if status_name == "PASS" else "Codex built-in doctor reported findings",
            {"failures": failures, "warnings": warnings, "contextual_non_tty": contextual, "duration_ms": result.duration_ms},
        )


def overall_status(checks: Iterable[Check]) -> str:
    values = list(checks)
    if not values:
        return "UNKNOWN"
    return max((check.status for check in values), key=lambda status: STATUS_ORDER[status])


def render_text(checks: list[Check], generated_at: str) -> str:
    overall = overall_status(checks)
    counts = Counter(check.status for check in checks)
    lines = [
        "Codex Environment Doctor",
        f"Generated: {generated_at}",
        f"Overall: {overall} | PASS {counts['PASS']} WARN {counts['WARN']} FAIL {counts['FAIL']} UNKNOWN {counts['UNKNOWN']}",
    ]
    categories: dict[str, list[Check]] = defaultdict(list)
    for check in checks:
        categories[check.category].append(check)
    for category in sorted(categories):
        lines.append("")
        lines.append(f"[{category}]")
        for check in categories[category]:
            lines.append(f"{check.status:7} {check.id}: {check.summary}")
            for key, value in check.details.items():
                if value not in (None, "", [], {}):
                    lines.append(f"         {key}: {json.dumps(value, ensure_ascii=False)}")
            if check.remediation:
                lines.append(f"         remediation: {check.remediation}")
    return "\n".join(lines)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Read-only Codex environment health checks")
    parser.add_argument("--config", default=str(Path.home() / ".codex" / "config.toml"), help="Codex config.toml path")
    parser.add_argument("--cwd", default=os.getcwd(), help="Working directory used for trust and repo skill checks")
    parser.add_argument("--network", action="store_true", help="Query Brain remote SHA, Jenkins API, Aliyun STS, Plane identity, and glab auth")
    parser.add_argument("--mcp-probe", action="store_true", help="Start Chrome DevTools MCP and call list_pages")
    parser.add_argument("--codex-doctor", action="store_true", help="Run and summarize codex doctor --json")
    parser.add_argument("--all", action="store_true", help="Enable --network, --mcp-probe, and --codex-doctor")
    parser.add_argument("--json", action="store_true", help="Emit JSON")
    args = parser.parse_args(argv)
    if args.all:
        args.network = args.mcp_probe = args.codex_doctor = True
    return args


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    generated_at = dt.datetime.now(dt.timezone.utc).isoformat()
    doctor = Doctor(args)
    checks = doctor.run()
    overall = overall_status(checks)
    if args.json:
        payload = {
            "schema_version": 1,
            "generated_at": generated_at,
            "overall_status": overall,
            "environment": {
                "platform": platform.system().lower(),
                "architecture": platform.machine(),
                "cwd": str(doctor.cwd),
                "config": str(doctor.config_path),
                "network_checked": args.network,
                "mcp_probed": args.mcp_probe,
                "codex_doctor_run": args.codex_doctor,
            },
            "checks": [dataclasses.asdict(check) for check in checks],
        }
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print(render_text(checks, generated_at))
    return 1 if overall == "FAIL" else 0


if __name__ == "__main__":
    raise SystemExit(main())
