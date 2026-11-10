#!/usr/bin/env python3
"""Opt-in adapters around the existing runtimes; never replaces the Codex launcher."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import subprocess
import sys

import baseline
import claude_adapter
import config_policy
import handoff


DEFAULT_STATE = Path.home() / ".local/state/agent-runtime"


def canonical(path):
    try:
        return Path(path).expanduser().resolve(strict=False)
    except (OSError, RuntimeError) as error:
        raise ValueError("Cannot resolve the requested state/output path") from error


def reject_protected(path, extra_protected=()):
    """These adapters never write Codex/shared sources, including via aliases."""
    home = Path.home()
    vault = home / "Code/Obsidian Vault"
    protected = baseline.default_codex_paths(home, vault) + [
        home / ".codex", home / ".agents", home / ".brain", vault / "brain",
    ] + list(extra_protected)
    requested = canonical(path)
    for root in protected:
        root = canonical(root)
        if requested == root or requested.is_relative_to(root):
            raise ValueError("Codex/shared sources are protected from runtime writes")
    return requested


def state_path(path, state, extra_protected=(), preserve=()):
    """Only write artifacts below the explicit private state root."""
    state = reject_protected(state, extra_protected)
    if state.exists() and not state.is_dir():
        raise ValueError("State directory must be a directory")
    original = Path(path).expanduser().absolute()
    if original.is_symlink():
        raise ValueError("State/output paths must not be symlinks")
    requested = reject_protected(original, extra_protected)
    if not requested.is_relative_to(state):
        raise ValueError("State/output paths must stay within --state-dir")
    for source in preserve:
        source = canonical(source)
        if requested == source or (requested.exists() and source.exists()
                                   and requested.samefile(source)):
            raise ValueError("Output must not overwrite an input snapshot")
    return requested


def emit(data):
    print(json.dumps(data, ensure_ascii=False, indent=2))


def profiles(state):
    path = state_path(state / "profiles.json", state)
    data = json.loads(path.read_text())
    if data.get("schema_version") != 1:
        raise ValueError("Unsupported profile schema")
    return data


def initialize(state):
    path = state_path(state / "profiles.json", state)
    if path.exists():
        raise ValueError("Profiles already exist; do not overwrite local choices")
    home = Path.home()
    vault = home / "Code/Obsidian Vault"
    data = {
        "schema_version": 1,
        "baseline_agent": "codex",
        "protected_contract": "Codex config, hooks, MCP, shared sources, auth and memories are not installation targets.",
        "brain": {
            "adapter": str(vault / ".agents/tools/brain-context/brain_context.py"),
            "vault_root": str(vault),
            "personal": {"root": str(vault / "brain")},
            "work": {"root": str(home / ".brain"), "profile": str(home / ".brain/.agents/skills/weekly-report/profiles/work.json")},
        },
        "providers": {
            "subscription": ["codex", "skywork", "cursor", "grok"],
            "other_agents": "magpie", "cc_switch": "inactive",
        },
        "claude": {
            "mcp_source": str(home / ".config/magpie/library.json"),
            "mcp_destination": str(home / ".claude.json"),
            "mcp_names": ["context7", "chrome-devtools", "magpie-image"],
            "managed_by": "magpie", "materialized_by": "agent-runtime/claude_adapter",
            "skills": ["brain", "multi-repo-maintenance"],
        },
        "optional_capabilities": {"codex": ["computer-use", "native connectors", "node_repl"]},
    }
    handoff.atomic_json(path, data)
    return {"status": "created", "profile": str(path), "codex_modified": False}


def brain_call(state, scope, command, path=None, sha256=None, metadata_only=False, query=None):
    data = profiles(state)["brain"]
    selected = data[scope]
    args = [sys.executable, "-B", data["adapter"], "--vault-root", data["vault_root"],
            "--scope", scope, "--brain-dir", selected["root"]]
    if scope == "work":
        args += ["--work-profile", selected["profile"]]
    args += [command]
    if command == "read":
        if not path or not sha256:
            raise ValueError("Read requires a relative source path and expected SHA256")
        args += [path, "--sha256", sha256]
    elif command == "search":
        if not query:
            raise ValueError("Search requires a topic")
        args += [query]
    result = subprocess.run(args, capture_output=True, text=True, timeout=60)
    if result.returncode:
        raise ValueError("Scoped Brain adapter rejected the request; no fallback was used")
    output = json.loads(result.stdout)
    if metadata_only:
        output.pop("content", None)
        # Search summaries can contain private source content; metadata mode keeps identity only.
        for key in ("results", "preferences"):
            if key in output:
                output[key] = [{k: v for k, v in item.items() if k in ("path", "sha256", "line", "total_lines")}
                               for item in output[key]]
    return output


def parser():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--state-dir", type=Path, default=DEFAULT_STATE)
    sub = p.add_subparsers(dest="command", required=True)
    sub.add_parser("init")
    base = sub.add_parser("baseline")
    bs = base.add_subparsers(dest="operation", required=True)
    snap = bs.add_parser("capture")
    snap.add_argument("--output", type=Path, required=True)
    snap.add_argument("--vault-root", type=Path, required=True)
    snap.add_argument("--extra-source", type=Path, action="append", default=[])
    check = bs.add_parser("check")
    check.add_argument("--snapshot", type=Path, required=True)
    check.add_argument("--output", type=Path)
    brain = sub.add_parser("brain")
    brain.add_argument("--scope", choices=["personal", "work"], required=True)
    brain.add_argument("--metadata-only", action="store_true")
    brain.add_argument("operation", choices=["verify", "search", "read"])
    brain.add_argument("value", nargs="?")
    brain.add_argument("--sha256")
    mcp = sub.add_parser("claude-mcp")
    mcp.add_argument("operation", choices=["plan", "apply", "rollback"])
    mcp.add_argument("--backup-dir", type=Path)
    mcp.add_argument("--manifest", type=Path)
    task = sub.add_parser("handoff")
    task.add_argument("operation", choices=["create", "read", "verify", "release", "claim"])
    task.add_argument("--file", type=Path, required=True)
    task.add_argument("--root", type=Path)
    task.add_argument("--owner")
    task.add_argument("--revision", type=int)
    task.add_argument("--goal")
    task.add_argument("--next-step")
    task.add_argument("--scope", choices=["personal", "work"])
    task.add_argument("--protect", action="append", default=[])
    task.add_argument("--constraint", action="append", default=[])
    task.add_argument("--verification-json", help="Reported verification records; receiver still checks the evidence")
    return p


def main():
    args = parser().parse_args()
    try:
        if args.command == "init":
            result = initialize(args.state_dir)
        elif args.command == "baseline":
            if args.operation == "capture":
                sources = baseline.default_codex_paths(Path.home(), args.vault_root) + args.extra_source
                output = state_path(args.output, args.state_dir, extra_protected=sources)
                if output.exists():
                    raise ValueError("Do not overwrite an existing baseline")
                result = baseline.capture(sources)
                config = Path.home() / ".codex/config.toml"
                if config.is_file() and str(config) in result["entries"]:
                    result["codex_config_policy"] = config_policy.capture(config)
                    if result["entries"][str(config)]["sha256"] != result["codex_config_policy"]["raw_sha256"]:
                        raise ValueError("Codex config changed during capture; capture again")
                if result["errors"]:
                    emit({"status": "error", "errors": result["errors"]})
                    return 2
                handoff.atomic_json(output, result)
                result = {"status": "captured", "entries": len(result["entries"]), "snapshot": str(output)}
            else:
                before = json.loads(args.snapshot.read_text())
                output = state_path(args.output, args.state_dir,
                                    extra_protected=[Path(p) for p in before["roots"]],
                                    preserve=[args.snapshot]) if args.output else None
                after = baseline.capture([Path(p) for p in before["roots"]])
                result = baseline.compare(before, after)
                if "codex_config_policy" in before:
                    config = Path.home() / ".codex/config.toml"
                    after["codex_config_policy"] = config_policy.capture(config)
                    if after["entries"][str(config)]["sha256"] != after["codex_config_policy"]["raw_sha256"]:
                        raise ValueError("Codex config changed during check; check again")
                    result = config_policy.apply_to_comparison(result, before, after, config)
                if output:
                    handoff.atomic_json(output, result)
        elif args.command == "brain":
            result = brain_call(args.state_dir, args.scope, args.operation, args.value, args.sha256,
                                args.metadata_only, args.value)
        elif args.command == "claude-mcp":
            if args.operation == "rollback":
                if args.manifest is None:
                    raise ValueError("Rollback requires the exact installation manifest")
                manifest = state_path(args.manifest, args.state_dir)
                manifest_data = json.loads(manifest.read_text())
                reject_protected(manifest_data["config_path"])
                result = claude_adapter.rollback(manifest)
            else:
                backup = None
                if args.operation == "apply":
                    if args.backup_dir is None:
                        raise ValueError("Apply requires a private backup directory")
                    backup = state_path(args.backup_dir, args.state_dir)
                profile = profiles(args.state_dir)["claude"]
                reject_protected(profile["mcp_destination"])
                servers = claude_adapter.load_magpie_servers(Path(profile["mcp_source"]), profile["mcp_names"],
                                                            profile.get("launch_overrides"))
                prepared = claude_adapter.plan(Path(profile["mcp_destination"]), servers)
                if args.operation == "plan":
                    # Never print prepared: it contains configuration and credentials.
                    result = {"status": "compatible", "names": sorted(servers), "source": "magpie", "destination": "claude user MCP"}
                else:
                    result = claude_adapter.apply(prepared, backup)
        elif args.command == "handoff":
            task_file = state_path(args.file, args.state_dir)
            if args.operation == "create":
                if args.root is None:
                    raise ValueError("Create requires an explicit worktree root")
                result = handoff.create(task_file, args.root, args.owner, args.goal, args.next_step,
                                        args.scope, args.protect, args.constraint)
            elif args.operation == "read":
                result = handoff.load(task_file)
            elif args.operation == "verify":
                result = handoff.inspect(task_file)
            elif args.operation == "release":
                verification = json.loads(args.verification_json) if args.verification_json else None
                if verification is not None and (not isinstance(verification, list) or
                                                   not all(isinstance(item, dict) for item in verification)):
                    raise ValueError("Verification must be a JSON list of records")
                result = handoff.release(task_file, args.owner, args.revision, args.next_step, verification)
            else:
                result = handoff.claim(task_file, args.owner, args.revision)
        emit(result)
        return 0 if result.get("ok", True) else 2
    except (ValueError, OSError, KeyError, subprocess.SubprocessError) as error:
        # Adapter errors are deliberately sanitized; no raw subprocess stderr/env.
        emit({"status": "error", "error": str(error)})
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
