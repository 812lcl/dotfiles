import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


SCRIPT = Path(__file__).parents[1] / "scripts" / "codex_env_doctor.py"
SPEC = importlib.util.spec_from_file_location("codex_env_doctor", SCRIPT)
doctor = importlib.util.module_from_spec(SPEC)
assert SPEC.loader
sys.modules[SPEC.name] = doctor
SPEC.loader.exec_module(doctor)


class DoctorHelpersTest(unittest.TestCase):
    def test_hook_commands_extract_nested_commands(self):
        config = {
            "hooks": {
                "Stop": [{"hooks": [{"type": "command", "command": "brain sync --quiet --background"}]}]
            }
        }
        self.assertEqual(doctor.hook_commands(config, "Stop"), ["brain sync --quiet --background"])

    def test_frontmatter_requires_name_and_description(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "SKILL.md"
            path.write_text("---\nname: test-skill\ndescription: Test it.\n---\nBody\n", encoding="utf-8")
            metadata, error = doctor.parse_frontmatter(path)
        self.assertIsNone(error)
        self.assertEqual(metadata["name"], "test-skill")
        self.assertEqual(metadata["description"], "Test it.")

    def test_frontmatter_supports_folded_description(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "SKILL.md"
            path.write_text("---\nname: test-skill\ndescription: >\n  First line.\n  Second line.\n---\n", encoding="utf-8")
            metadata, error = doctor.parse_frontmatter(path)
        self.assertIsNone(error)
        self.assertEqual(metadata["description"], "First line. Second line.")

    def test_overall_status_uses_highest_severity(self):
        checks = [
            doctor.Check("a", "x", "PASS", "ok"),
            doctor.Check("b", "x", "UNKNOWN", "skip"),
            doctor.Check("c", "x", "WARN", "risk"),
        ]
        self.assertEqual(doctor.overall_status(checks), "WARN")
        checks.append(doctor.Check("d", "x", "FAIL", "broken"))
        self.assertEqual(doctor.overall_status(checks), "FAIL")

    def test_skill_roots_include_user_and_system(self):
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            (home / ".codex" / "skills" / ".system").mkdir(parents=True)
            roots = doctor.skill_roots(home, home)
        scopes = [scope for scope, _ in roots]
        self.assertIn("user", scopes)
        self.assertIn("system", scopes)

    def test_app_server_command_disables_only_enabled_mcp_servers(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            args = doctor.argparse.Namespace(cwd=str(root), config=str(root / "config.toml"))
            instance = doctor.Doctor(args)
            instance.config = {
                "mcp_servers": {
                    "chrome-devtools": {"enabled": True},
                    "disabled-server": {"enabled": False},
                }
            }
            command = instance.app_server_command("codex", strict=True, disable_mcp=True)

        self.assertEqual(command[:3], ["codex", "app-server", "--strict-config"])
        self.assertIn("mcp_servers.chrome-devtools.enabled=false", command)
        self.assertNotIn("mcp_servers.disabled-server.enabled=false", command)
        self.assertEqual(command[-1], "--stdio")

    def test_disabled_skill_is_excluded_from_duplicate_and_budget_checks(self):
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            user_skill = home / ".agents" / "skills" / "skill-creator" / "SKILL.md"
            system_skill = home / ".codex" / "skills" / ".system" / "skill-creator" / "SKILL.md"
            for path in (user_skill, system_skill):
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(
                    "---\nname: skill-creator\ndescription: Create skills.\n---\nBody\n",
                    encoding="utf-8",
                )
            config_path = home / ".codex" / "config.toml"
            args = doctor.argparse.Namespace(cwd=str(home), config=str(config_path))
            instance = doctor.Doctor(args)
            instance.home = home
            instance.config = {
                "skills": {
                    "config": [{"path": str(user_skill), "enabled": False}],
                }
            }
            runtime = {
                "complete": True,
                "runtime_skills": 2,
                "enabled_skills": 1,
                "load_errors": 0,
                "missing_names": [],
            }
            with mock.patch.object(instance, "check_skill_runtime", return_value=runtime):
                instance.check_skills()

        duplicate = next(check for check in instance.checks if check.id == "skills.duplicates")
        metadata = next(check for check in instance.checks if check.id == "skills.metadata_budget")
        self.assertEqual(duplicate.status, "PASS")
        self.assertEqual(metadata.status, "PASS")
        self.assertEqual(metadata.details["enabled_skills_on_disk"], 1)

    def test_complete_runtime_inventory_overrides_metadata_pressure_heuristic(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            args = doctor.argparse.Namespace(cwd=str(root), config=str(root / "config.toml"))
            instance = doctor.Doctor(args)
            record = doctor.SkillRecord(
                "large-skill",
                "x" * 9000,
                root / "large-skill",
                root / "large-skill" / "SKILL.md",
                "user",
                10,
            )
            runtime = {
                "complete": True,
                "runtime_skills": 1,
                "enabled_skills": 1,
                "load_errors": 0,
                "missing_names": [],
            }
            instance.check_skill_metadata([record], runtime)

        check = instance.checks[0]
        self.assertEqual(check.status, "PASS")
        self.assertTrue(check.details["heuristic_pressure"])

    def test_mcp_probe_retries_list_pages_timeout_once(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            args = doctor.argparse.Namespace(cwd=str(root), config=str(root / "config.toml"))
            instance = doctor.Doctor(args)
            timeout = {
                "status": "FAIL",
                "summary": "Chrome DevTools MCP list_pages timed out",
                "details": {"tool_count": 29},
            }
            success = {
                "status": "PASS",
                "summary": "Chrome DevTools MCP initialized, listed tools, and completed list_pages",
                "details": {"tool_count": 29},
            }
            with mock.patch.object(instance, "_probe_stdio_mcp_once", side_effect=[timeout, success]) as probe:
                with mock.patch.object(doctor.time, "sleep"):
                    result = instance.probe_stdio_mcp({})

        self.assertEqual(result["status"], "PASS")
        self.assertEqual(result["details"]["attempts"], 2)
        self.assertEqual(probe.call_count, 2)

    def test_env_assignments_parse_shell_quotes_without_exposing_values(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / ".env"
            path.write_text(
                "JENKINS_URL='https://jenkins.example.test'\n"
                "export JENKINS_USER=doctor-user # comment\n"
                "JENKINS_TOKEN=super-secret\n",
                encoding="utf-8",
            )
            values, invalid = doctor.load_env_assignments(path, doctor.JENKINS_ENV_KEYS)
        self.assertEqual(set(values), set(doctor.JENKINS_ENV_KEYS))
        self.assertEqual(invalid, [])
        self.assertTrue(doctor.valid_jenkins_url(values["JENKINS_URL"]))

    def test_jenkins_local_checks_do_not_emit_credential_values(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            helper = root / "brain" / "tools" / "jenkins.sh"
            helper.parent.mkdir(parents=True)
            helper.write_text(
                "#!/bin/bash\n"
                "# JENKINS_URL JENKINS_USER JENKINS_TOKEN /api/json\n",
                encoding="utf-8",
            )
            helper.chmod(0o700)
            env_file = root / ".env"
            env_file.write_text(
                "JENKINS_URL=https://jenkins.example.test\n"
                "JENKINS_USER=doctor-user\n"
                "JENKINS_TOKEN=super-secret\n",
                encoding="utf-8",
            )
            env_file.chmod(0o600)
            args = doctor.argparse.Namespace(cwd=str(root), config=str(root / "config.toml"), network=False)
            instance = doctor.Doctor(args)
            with mock.patch.dict(doctor.os.environ, {}, clear=False):
                for name in (*doctor.JENKINS_ENV_KEYS, "SKYWORK_AGENT_ROOT"):
                    doctor.os.environ.pop(name, None)
                instance.check_jenkins()
            report = json.dumps([doctor.dataclasses.asdict(check) for check in instance.checks])
        self.assertNotIn("doctor-user", report)
        self.assertNotIn("super-secret", report)
        self.assertEqual(next(check.status for check in instance.checks if check.id == "jenkins.tool"), "PASS")
        self.assertEqual(next(check.status for check in instance.checks if check.id == "jenkins.env.file"), "PASS")

    def test_jenkins_api_probe_reports_only_boolean_identity_state(self):
        class Response:
            status = 200

            def __init__(self, payload):
                self.payload = json.dumps(payload).encode()

            def __enter__(self):
                return self

            def __exit__(self, *_args):
                return False

            def read(self, _limit):
                return self.payload

        responses = [Response({"authenticated": True, "name": "doctor-user"}), Response({"mode": "NORMAL"})]
        credentials = {
            "JENKINS_URL": "https://jenkins.example.test",
            "JENKINS_USER": "doctor-user",
            "JENKINS_TOKEN": "super-secret",
        }
        with mock.patch.object(doctor.urllib.request, "urlopen", side_effect=responses):
            result = doctor.probe_jenkins_api(credentials)
        report = json.dumps(result)
        self.assertEqual(result["status"], "PASS")
        self.assertNotIn("doctor-user", report)
        self.assertNotIn("super-secret", report)

    def test_aliyun_checks_do_not_emit_credentials_or_identity(self):
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            config = home / ".aliyun" / "config.json"
            config.parent.mkdir(parents=True)
            config.write_text(
                json.dumps(
                    {
                        "current": "doctor-profile",
                        "profiles": [
                            {
                                "name": "doctor-profile",
                                "mode": "AK",
                                "access_key_id": "LTAI-DO-NOT-PRINT",
                                "access_key_secret": "aliyun-super-secret",
                                "region_id": "cn-test-identity",
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )
            config.chmod(0o600)
            args = doctor.argparse.Namespace(cwd=str(home), config=str(home / "config.toml"), network=True)
            instance = doctor.Doctor(args)
            instance.home = home
            results = [
                doctor.CommandResult(0, "3.3.12\n", "", 2),
                doctor.CommandResult(
                    0,
                    '{"AccountId":"123456789","Arn":"acs:ram::123456789:user/doctor"}',
                    "",
                    20,
                ),
            ]
            with mock.patch.object(doctor.shutil, "which", return_value="/usr/bin/aliyun"):
                with mock.patch.object(doctor, "run_command", side_effect=results):
                    instance.check_aliyun()
            report = json.dumps([doctor.dataclasses.asdict(check) for check in instance.checks])

        self.assertNotIn("LTAI-DO-NOT-PRINT", report)
        self.assertNotIn("aliyun-super-secret", report)
        self.assertNotIn("123456789", report)
        self.assertNotIn("doctor-profile", report)
        self.assertEqual(next(check.status for check in instance.checks if check.id == "aliyun.cli"), "PASS")
        self.assertEqual(next(check.status for check in instance.checks if check.id == "aliyun.config"), "PASS")
        self.assertEqual(next(check.status for check in instance.checks if check.id == "aliyun.api"), "PASS")

    def test_aliyun_failure_is_classified_without_raw_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            config = home / ".aliyun" / "config.json"
            config.parent.mkdir(parents=True)
            config.write_text(
                json.dumps(
                    {
                        "current": "default",
                        "profiles": [
                            {
                                "name": "default",
                                "mode": "AK",
                                "access_key_id": "secret-ak-id",
                                "access_key_secret": "secret-ak-value",
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )
            config.chmod(0o600)
            args = doctor.argparse.Namespace(cwd=str(home), config=str(home / "config.toml"), network=True)
            instance = doctor.Doctor(args)
            instance.home = home
            results = [
                doctor.CommandResult(0, "3.3.12\n", "", 2),
                doctor.CommandResult(1, "", "InvalidAccessKeyId: secret-ak-id", 20),
            ]
            with mock.patch.object(doctor.shutil, "which", return_value="/usr/bin/aliyun"):
                with mock.patch.object(doctor, "run_command", side_effect=results):
                    instance.check_aliyun()
            report = json.dumps([doctor.dataclasses.asdict(check) for check in instance.checks])

        api = next(check for check in instance.checks if check.id == "aliyun.api")
        self.assertEqual(api.status, "FAIL")
        self.assertEqual(api.details["error_class"], "authentication")
        self.assertNotIn("secret-ak-id", report)
        self.assertNotIn("secret-ak-value", report)

    def test_brain_tools_are_validated_without_executing_entrypoints(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "brain"
            tools_dir = root / "tools"
            library_dir = tools_dir / "_lib"
            library_dir.mkdir(parents=True)
            python_tool = tools_dir / "doctor-tool.py"
            python_tool.write_text("#!/usr/bin/env python3\nimport json\n", encoding="utf-8")
            python_tool.chmod(0o755)
            shell_tool = tools_dir / "doctor-tool.sh"
            shell_tool.write_text("#!/usr/bin/env bash\nsource \"$SCRIPT_DIR/_lib/paths.sh\"\n", encoding="utf-8")
            shell_tool.chmod(0o755)
            library = library_dir / "paths.sh"
            library.write_text("#!/usr/bin/env bash\n", encoding="utf-8")
            library.chmod(0o755)
            args = doctor.argparse.Namespace(cwd=str(root), config=str(root / "config.toml"), network=False)
            instance = doctor.Doctor(args)

            def executable(name):
                return f"/usr/bin/{Path(name).name}"

            with mock.patch.object(instance, "brain_root", return_value=root):
                with mock.patch.object(instance, "executable", side_effect=executable):
                    with mock.patch.object(
                        doctor,
                        "run_command",
                        return_value=doctor.CommandResult(0, "doctor-tool.py  test\n", "", 1),
                    ) as command:
                        instance.check_brain_tools("brain")

        self.assertEqual(next(check.status for check in instance.checks if check.id == "brain.tools.inventory"), "PASS")
        self.assertEqual(next(check.status for check in instance.checks if check.id == "brain.tools.integrity"), "PASS")
        self.assertEqual(next(check.status for check in instance.checks if check.id == "brain.tools.dependencies"), "PASS")
        invoked = [call.args[0] for call in command.call_args_list]
        self.assertIn(["brain", "tools", "list"], invoked)
        self.assertFalse(any("doctor-tool.py" in args for args in invoked))


if __name__ == "__main__":
    unittest.main()
