"""Read-only Codex config comparison allowing the user's two model selectors."""
import hashlib
import json
from pathlib import Path
import tomllib


IGNORED_FIELDS = ("model", "model_reasoning_effort")


def capture(path):
    path = Path(path)
    before = path.stat()
    raw = path.read_bytes()
    data = tomllib.loads(raw.decode())
    for name in IGNORED_FIELDS:
        data.pop(name, None)
    # Unsupported values fail closed rather than hiding unrelated settings.
    normalized = json.dumps(data, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
    after = path.stat()
    identity = lambda s: (s.st_dev, s.st_ino, s.st_mode, s.st_size, s.st_mtime_ns, s.st_ctime_ns)
    if identity(before) != identity(after):
        raise ValueError("Config changed during capture")
    return {"policy_version": 1, "ignored_top_level_fields": list(IGNORED_FIELDS),
            "resolved_path": str(path.resolve()), "mode": after.st_mode & 0o777,
            "raw_sha256": hashlib.sha256(raw).hexdigest(),
            "other_fields_sha256": hashlib.sha256(normalized).hexdigest()}


def compare(before, after):
    required = ("policy_version", "ignored_top_level_fields", "resolved_path", "mode", "other_fields_sha256")
    ok = all(before.get(key) == after.get(key) for key in required)
    return {"ok": ok, "raw_changed": before["raw_sha256"] != after["raw_sha256"],
            "ignored_top_level_fields": list(IGNORED_FIELDS)}


def apply_to_comparison(result, before, after, config_path):
    """Use new snapshot evidence only; old full-file hashes remain conservative."""
    if "codex_config_policy" not in before:
        return result
    policy = compare(before["codex_config_policy"], after["codex_config_policy"])
    path = str(config_path)
    metadata = lambda entry: {k: v for k, v in entry.items() if k not in ("sha256", "size")}
    same_metadata = metadata(before["entries"][path]) == metadata(after["entries"][path])
    policy["ok"] = policy["ok"] and same_metadata
    result = dict(result)
    result["observed_raw_changed"] = list(result["changed"])
    if policy["ok"]:
        result["changed"] = [p for p in result["changed"] if p != path]
    result["ok"] = policy["ok"] and not any(result[k] for k in ("added", "removed", "changed", "errors"))
    result["codex_config_policy"] = policy
    return result
