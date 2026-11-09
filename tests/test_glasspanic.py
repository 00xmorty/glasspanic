#!/usr/bin/env python3
"""Tests for glasspanic. Run: python3 -m unittest discover -s tests -v

Every test drives the real CLI through PATH stubs, so no real macOS
preference is read or written by this suite.
"""

import json
import os
import shutil
import stat
import subprocess
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CLI = os.path.join(ROOT, "glasspanic")

DEFAULTS_STUB = r"""#!/bin/sh
store="${GP_STORE:?}"
cmd="$1"
shift
case "$cmd" in
  read)
    dom="$1"; key="$2"
    if [ -f "$store" ]; then
      while IFS="$(printf '\t')" read -r d k v; do
        if [ "$d" = "$dom" ] && [ "$k" = "$key" ]; then printf '%s\n' "$v"; exit 0; fi
      done < "$store"
    fi
    printf 'The domain/default pair of (%s, %s) does not exist\n' "$dom" "$key" >&2
    exit 1
    ;;
  write)
    dom="$1"; key="$2"; shift 2
    [ "${1:-}" = "-bool" ] && shift
    val="$1"
    [ "${GP_IGNORE_WRITE:-0}" = "1" ] && exit 0
    [ -f "$store" ] || : > "$store"
    awk -F'\t' -v d="$dom" -v k="$key" '$1!=d || $2!=k' "$store" > "$store.tmp"
    printf '%s\t%s\t%s\n' "$dom" "$key" "$val" >> "$store.tmp"
    mv "$store.tmp" "$store"
    exit 0
    ;;
  *) exit 1 ;;
esac
"""

SW_VERS_STUB = r"""#!/bin/sh
case "$1" in
  -productVersion) printf '%s\n' "${GP_VER:-26.6.2}" ;;
  -buildVersion)   printf '%s\n' "${GP_BUILD:-25G83}" ;;
  *) exit 1 ;;
esac
"""

UNAME_STUB = r"""#!/bin/sh
if [ "$1" = "-s" ]; then printf '%s\n' "${GP_UNAME:-Darwin}"; else /usr/bin/uname "$@"; fi
"""

PGREP_STUB = r"""#!/bin/sh
name="$2"
case " ${GP_RUNNING:-} " in *" $name "*) exit 0 ;; *) exit 1 ;; esac
"""

KILLALL_STUB = r"""#!/bin/sh
printf '%s\n' "$1" >> "${GP_KILL_LOG:?}"
exit 0
"""


class GlassPanicTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="glasspanic-")
        self.bin = os.path.join(self.tmp, "bin")
        os.makedirs(self.bin)
        for name, body in (
            ("defaults", DEFAULTS_STUB),
            ("sw_vers", SW_VERS_STUB),
            ("uname", UNAME_STUB),
            ("pgrep", PGREP_STUB),
            ("killall", KILLALL_STUB),
        ):
            path = os.path.join(self.bin, name)
            with open(path, "w") as fh:
                fh.write(body)
            os.chmod(path, os.stat(path).st_mode | stat.S_IEXEC)
        self.store = os.path.join(self.tmp, "store.tsv")
        self.kill_log = os.path.join(self.tmp, "kill.log")
        open(self.store, "w").close()

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def run_cli(self, *args, **env_extra):
        env = {
            "PATH": self.bin + ":/usr/bin:/bin",
            "HOME": self.tmp,
            "GP_STORE": self.store,
            "GP_KILL_LOG": self.kill_log,
            "GP_RUNNING": "SystemUIServer",
        }
        env.update(env_extra)
        proc = subprocess.run(
            ["zsh", CLI, *args],
            capture_output=True, text=True, env=env, timeout=60,
        )
        return proc

    def json_out(self, proc):
        self.assertEqual(proc.returncode, 0, proc.stderr)
        return json.loads(proc.stdout)

    # -- doctor / json ------------------------------------------------------
    def test_json_schema(self):
        data = self.json_out(self.run_cli("--json"))
        self.assertEqual(data["tool"], "glasspanic")
        self.assertIs(data["read_only"], True)
        self.assertIs(data["sudo_used"], False)
        self.assertIs(data["network_used"], False)
        self.assertEqual(len(data["symptoms"]), 4)
        self.assertEqual(
            [s["id"] for s in data["symptoms"]],
            ["blank_dialog", "menus_vanish", "menubar_clicks", "third_party_panel"],
        )
        for s in data["symptoms"]:
            for field in ("title", "signal", "first_step", "evidence"):
                self.assertTrue(s[field].strip(), field)

    def test_unwritten_key_is_unset_not_false(self):
        data = self.json_out(self.run_cli("--json"))
        prefs = {p["key"]: p for p in data["view_settings"]}
        self.assertEqual(prefs["reduceTransparency"]["state"], "unset")
        self.assertEqual(prefs["reduceTransparency"]["value"], "")
        self.assertNotEqual(prefs["reduceTransparency"]["value"], "0")

    def test_present_key_is_reported(self):
        with open(self.store, "w") as fh:
            fh.write("com.apple.Accessibility\tReduceMotionEnabled\t0\n")
        data = self.json_out(self.run_cli("--json"))
        prefs = {p["key"]: p for p in data["view_settings"]}
        self.assertEqual(prefs["ReduceMotionEnabled"]["state"], "present")
        self.assertEqual(prefs["ReduceMotionEnabled"]["value"], "0")

    def test_text_output_has_no_stray_assignments(self):
        proc = self.run_cli()
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertNotIn("shown=", proc.stdout)
        self.assertIn("SYMPTOM MAP", proc.stdout)
        self.assertIn("Stored values are not proof", proc.stdout)

    def test_non_macos_is_reported_not_guessed(self):
        proc = self.run_cli("--json", GP_UNAME="Linux")
        data = self.json_out(proc)
        self.assertEqual(data["system"]["platform"], "Linux")
        for pref in data["view_settings"]:
            self.assertEqual(pref["state"], "unsupported")

    # -- apply / revert -----------------------------------------------------
    def test_apply_writes_and_verifies_readback(self):
        proc = self.run_cli("--apply")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn("read-back verified", proc.stdout)
        self.assertIn("--revert", proc.stdout)
        data = self.json_out(self.run_cli("--json"))
        prefs = {p["key"]: p for p in data["view_settings"]}
        self.assertEqual(prefs["reduceTransparency"]["value"], "true")

    def test_apply_does_not_claim_success_when_write_does_not_stick(self):
        proc = self.run_cli("--apply", GP_IGNORE_WRITE="1")
        self.assertEqual(proc.returncode, 3)
        self.assertNotIn("read-back verified", proc.stdout)
        self.assertIn("Not claiming success", proc.stderr)

    def test_revert_stores_false(self):
        self.run_cli("--apply")
        proc = self.run_cli("--revert")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        data = self.json_out(self.run_cli("--json"))
        prefs = {p["key"]: p for p in data["view_settings"]}
        self.assertEqual(prefs["reduceTransparency"]["value"], "false")

    def test_print_only_changes_nothing(self):
        proc = self.run_cli("--apply", "--print")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn("would run:", proc.stdout)
        with open(self.store) as fh:
            self.assertNotIn("reduceTransparency", fh.read())

    def test_apply_refused_off_macos(self):
        proc = self.run_cli("--apply", GP_UNAME="Linux")
        self.assertEqual(proc.returncode, 2)
        self.assertFalse(os.path.exists(self.kill_log))

    # -- nudge --------------------------------------------------------------
    def test_nudge_refuses_without_confirmation_in_noninteractive(self):
        proc = self.run_cli("--nudge")
        self.assertEqual(proc.returncode, 2)
        self.assertIn("--yes", proc.stderr)
        self.assertFalse(os.path.exists(self.kill_log))

    def test_nudge_with_yes_restarts_only_running_agents(self):
        proc = self.run_cli("--nudge", "--yes", GP_RUNNING="SystemUIServer")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        with open(self.kill_log) as fh:
            killed = [line.strip() for line in fh if line.strip()]
        self.assertEqual(killed, ["SystemUIServer"])

    def test_nudge_when_no_agent_running_is_a_noop(self):
        proc = self.run_cli("--nudge", "--yes", GP_RUNNING="")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertFalse(os.path.exists(self.kill_log))

    # -- interface / safety -------------------------------------------------
    def test_unknown_argument_exits_2(self):
        proc = self.run_cli("--fix-everything")
        self.assertEqual(proc.returncode, 2)
        self.assertIn("unknown argument", proc.stderr)

    def test_source_has_no_sudo_or_destructive_commands(self):
        with open(CLI) as fh:
            body = fh.read()
        for banned in ("sudo ", "rm -", "rm -rf", "curl ", "wget ", "killall -9"):
            self.assertNotIn(banned, body, f"found banned pattern: {banned}")

    def test_help_and_version(self):
        self.assertIn("Usage:", self.run_cli("--help").stdout)
        self.assertIn("0.1.0", self.run_cli("--version").stdout)


if __name__ == "__main__":
    unittest.main()
