import hashlib
import json
from pathlib import Path
import stat
import tempfile
import unittest
from unittest.mock import patch

import claude_adapter as adapter


class AdapterTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.config = self.root / "claude.json"
        self.backups = self.root / "state" / "backups"
        self.servers = {"context7": {"type": "stdio", "command": "npx",
                                    "args": ["-y", "example-mcp"],
                                    "env": {"TOKEN": "private-test-secret"}}}

    def tearDown(self):
        self.temp.cleanup()

    def write(self, value, mode=0o600):
        self.config.write_text(json.dumps(value))
        self.config.chmod(mode)

    def read(self):
        return json.loads(self.config.read_text())

    def apply(self):
        return adapter.apply(adapter.plan(self.config, self.servers), self.backups)

    def launch_fixture(self):
        library = self.root / "launch-library.json"
        library.write_text(json.dumps({"mcp": [{
            "name": "context7", "agents": ["claude", "codex"], "transport": "stdio",
            "command": "npx", "args": ["example-mcp", "--autoConnect"],
            "env": {"TOKEN": "source-secret"},
        }]}))
        executable = self.root / "local-node"
        executable.write_text("#!/bin/sh\nexit 0\n")
        executable.chmod(0o700)
        entry = self.root / "cached-entry.js"
        entry.write_text("// cached fixture; never executed\n")
        return library, {"command": str(executable),
                         "args": [str(entry), "--headless", "--user-data-dir=/isolated-profile"],
                         "entry_sha256": hashlib.sha256(entry.read_bytes()).hexdigest()}

    def test_verified_launch_override_preserves_source_env_and_omits_metadata(self):
        library, override = self.launch_fixture()
        before = library.read_bytes()
        output = adapter.load_magpie_servers(library, ["context7"], {"context7": override})
        self.assertEqual(output["context7"], {
            "type": "stdio", "command": override["command"], "args": override["args"],
            "env": {"TOKEN": "source-secret"},
        })
        self.assertNotIn("entry_sha256", output["context7"])
        self.assertEqual(library.read_bytes(), before)
        self.assertEqual(override["args"][1], "--headless")

    def test_launch_override_requires_matching_entry_hash(self):
        library, override = self.launch_fixture()
        for digest in ("0" * 64, "not-a-digest", None):
            with self.subTest(digest=digest):
                with self.assertRaises(adapter.AdapterError):
                    adapter.load_magpie_servers(library, ["context7"],
                                                {"context7": {**override, "entry_sha256": digest}})

    def test_launch_override_requires_absolute_existing_executable(self):
        library, override = self.launch_fixture()
        nonexec = self.root / "not-executable"
        nonexec.write_text("fixture")
        nonexec.chmod(0o600)
        for command in ("node", str(self.root / "missing-node"), str(nonexec), str(self.root)):
            with self.subTest(command=command):
                with self.assertRaises(adapter.AdapterError):
                    adapter.load_magpie_servers(library, ["context7"],
                                                {"context7": {**override, "command": command}})

    def test_launch_override_requires_absolute_regular_entry(self):
        library, override = self.launch_fixture()
        linked = self.root / "linked-entry.js"
        linked.symlink_to(override["args"][0])
        for args in ([], ["relative.js"], [str(self.root / "missing-entry.js")],
                     [str(self.root)], [str(linked)]):
            with self.subTest(args=args):
                with self.assertRaises(adapter.AdapterError):
                    adapter.load_magpie_servers(library, ["context7"],
                                                {"context7": {**override, "args": args}})

    def test_launch_override_rejects_unselected_names_and_non_mapping(self):
        library, override = self.launch_fixture()
        for overrides in ({"unselected": override}, []):
            with self.subTest(overrides_type=type(overrides).__name__):
                with self.assertRaises(adapter.AdapterError):
                    adapter.load_magpie_servers(library, ["context7"], overrides)

    def test_launch_override_rejects_remote_transports(self):
        library, override = self.launch_fixture()
        for transport in ("http", "sse"):
            library.write_text(json.dumps({"mcp": [{
                "name": "context7", "agents": ["claude"], "transport": transport,
                "url": "https://example.invalid/mcp", "headers": {"Authorization": "source"},
            }]}))
            with self.subTest(transport=transport):
                with self.assertRaises(adapter.AdapterError):
                    adapter.load_magpie_servers(library, ["context7"], {"context7": override})

    def test_launch_override_rejects_extra_or_missing_fields(self):
        library, override = self.launch_fixture()
        candidates = [{**override, key: "override-not-permitted"}
                      for key in ("env", "headers", "url", "type", "agents")]
        candidates.extend({key: value for key, value in override.items() if key != omitted}
                          for omitted in override)
        for value in candidates:
            with self.subTest(keys=sorted(value)):
                with self.assertRaises(adapter.AdapterError):
                    adapter.load_magpie_servers(library, ["context7"], {"context7": value})

    def test_magpie_selection_normalizes_transport_and_excludes_metadata(self):
        lib = self.root / "library.json"
        lib.write_text(json.dumps({"mcp": [
            {"name": "context7", "agents": ["claude", "codex"], "transport": "stdio",
             "command": "npx", "args": ["-y", "example-mcp"],
             "env": {"TOKEN": "private-test-secret"}, "description": "metadata"},
            {"name": "remote", "agents": ["claude"], "transport": "http",
             "url": "https://example.invalid/mcp", "headers": {"Authorization": "private"}},
        ]}))
        self.assertEqual(adapter.load_magpie_servers(lib, ["context7"]), self.servers)
        remote = adapter.load_magpie_servers(lib, ["remote"])["remote"]
        self.assertEqual(remote["type"], "http")
        self.assertNotIn("agents", remote)
        self.assertNotIn("name", remote)

    def test_magpie_requires_unique_claude_enabled_selection(self):
        lib = self.root / "library.json"
        lib.write_text(json.dumps({"mcp": [{"name": "other", "agents": ["codex"],
                                             "transport": "stdio", "command": "x"}]}))
        for names in (["other"], ["missing"], ["other", "other"]):
            with self.assertRaises(adapter.AdapterError):
                adapter.load_magpie_servers(lib, names)

    def test_new_file_is_private_and_rollback_removes_it(self):
        report = self.apply()
        self.assertEqual(self.read(), {"mcpServers": self.servers})
        self.assertEqual(stat.S_IMODE(self.config.stat().st_mode), 0o600)
        self.assertNotIn("private-test-secret", json.dumps(report))
        manifest = Path(report["manifest"])
        self.assertEqual(stat.S_IMODE(manifest.stat().st_mode), 0o600)
        self.assertEqual(stat.S_IMODE(manifest.parent.stat().st_mode), 0o700)
        self.assertEqual(stat.S_IMODE(self.backups.stat().st_mode), 0o700)
        self.assertEqual(adapter.rollback(manifest)["status"], "rolled_back")
        self.assertFalse(self.config.exists())
        self.assertEqual(adapter.rollback(manifest)["status"], "unchanged")

    def test_existing_unrelated_fields_mode_and_private_backup_are_preserved(self):
        self.write({"other": {"private": "value"}}, mode=0o640)
        before = self.config.read_bytes()
        report = self.apply()
        self.assertEqual(self.read()["other"], {"private": "value"})
        self.assertEqual(stat.S_IMODE(self.config.stat().st_mode), 0o640)
        backup = Path(report["manifest"]).parent / "config.before.json"
        self.assertEqual(backup.read_bytes(), before)
        self.assertEqual(stat.S_IMODE(backup.stat().st_mode), 0o600)
        adapter.rollback(Path(report["manifest"]))
        self.assertEqual(self.read(), {"other": {"private": "value"}})

    def test_idempotent_apply_has_no_backup_or_write(self):
        self.write({"mcpServers": self.servers, "other": 1})
        before = self.config.read_bytes()
        report = self.apply()
        self.assertEqual(report["status"], "unchanged")
        self.assertIsNone(report["manifest"])
        self.assertFalse(self.backups.exists())
        self.assertEqual(self.config.read_bytes(), before)

    def test_existing_conflict_fails_without_changes(self):
        self.write({"mcpServers": {"context7": {"command": "user-owned"}}})
        before = self.config.read_bytes()
        with self.assertRaises(adapter.ConflictError):
            self.apply()
        self.assertEqual(self.config.read_bytes(), before)
        self.assertFalse(self.backups.exists())

    def test_concurrent_edit_or_mode_change_rejects_plan(self):
        self.write({"other": 1})
        prepared = adapter.plan(self.config, self.servers)
        self.write({"other": 2})
        with self.assertRaises(adapter.ConflictError):
            adapter.apply(prepared, self.backups)
        prepared = adapter.plan(self.config, self.servers)
        self.config.chmod(0o640)
        with self.assertRaises(adapter.ConflictError):
            adapter.apply(prepared, self.backups)
        self.assertEqual(self.read(), {"other": 2})

    def test_last_moment_concurrent_edit_preserves_writer(self):
        self.write({"other": 1})
        prepared = adapter.plan(self.config, self.servers)
        original_snapshot = adapter._snapshot
        count = 0

        def concurrent_snapshot(path):
            nonlocal count
            count += 1
            if count == 3:  # Final CAS inside atomic replacement.
                self.write({"other": "concurrent"})
            return original_snapshot(path)

        with patch.object(adapter, "_snapshot", side_effect=concurrent_snapshot):
            with self.assertRaises(adapter.ConflictError):
                adapter.apply(prepared, self.backups)
        self.assertEqual(self.read(), {"other": "concurrent"})
        self.assertFalse(list(self.root.glob(".agent-runtime-*")))

    def test_rollback_preserves_unrelated_concurrent_changes_and_servers(self):
        self.write({"old": 1})
        report = self.apply()
        data = self.read()
        data["later"] = 2
        data["mcpServers"]["user-added"] = {"command": "keep"}
        self.write(data)
        adapter.rollback(Path(report["manifest"]))
        self.assertEqual(self.read(), {"old": 1, "later": 2,
                                       "mcpServers": {"user-added": {"command": "keep"}}})

    def test_rollback_conflict_leaves_every_entry_unchanged(self):
        self.servers["another"] = {"type": "stdio", "command": "keep"}
        report = self.apply()
        data = self.read()
        data["mcpServers"]["context7"]["command"] = "user-changed"
        self.write(data)
        before = self.config.read_bytes()
        with self.assertRaises(adapter.ConflictError):
            adapter.rollback(Path(report["manifest"]))
        self.assertEqual(self.config.read_bytes(), before)

    def test_rollback_keeps_preexisting_empty_mcp_object(self):
        self.write({"mcpServers": {}, "other": 1})
        report = self.apply()
        adapter.rollback(Path(report["manifest"]))
        self.assertEqual(self.read(), {"mcpServers": {}, "other": 1})

    def test_malformed_config_and_symlink_fail_closed(self):
        self.config.write_text("[]")
        with self.assertRaises(adapter.AdapterError):
            adapter.plan(self.config, self.servers)
        self.write({"mcpServers": []})
        with self.assertRaises(adapter.AdapterError):
            adapter.plan(self.config, self.servers)
        target = self.root / "target.json"
        self.config.rename(target)
        self.config.symlink_to(target)
        with self.assertRaises(adapter.AdapterError):
            adapter.plan(self.config, self.servers)

    def test_altered_plan_cannot_write_unrelated_fields(self):
        self.write({"other": 1})
        prepared = adapter.plan(self.config, self.servers)
        prepared["after"]["other"] = "not-authorized"
        with self.assertRaises(adapter.AdapterError):
            adapter.apply(prepared, self.backups)
        self.assertEqual(self.read(), {"other": 1})


if __name__ == "__main__":
    unittest.main()
