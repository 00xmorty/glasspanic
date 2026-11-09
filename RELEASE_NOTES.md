# Release notes

## v0.1.0 — 2026-11-09

First release. Triage for the macOS 27.2 Liquid Glass render bug.

**Added**

- Symptom map for four reported failure modes: `blank_dialog`, `menus_vanish`,
  `menubar_clicks`, `third_party_panel`. Each entry carries the signal, the first
  step to try, and the public source it is based on.
- View-setting probe that reports `present` / `unset` / `unsupported` per key.
  A key that was never written is reported as unset, never as `0`.
- `--apply` / `--revert` for `com.apple.universalaccess reduceTransparency` with
  read-back verification. An unverified write exits `3` and does not claim success.
- `--nudge` to restart `SystemUIServer` / `MenuBarAgent`, gated behind confirmation
  and `--yes` for non-interactive use.
- `--json` output for scripting, with `read_only`, `sudo_used` and `network_used`
  flags set explicitly.
- `--print` to show the command a mode would run without changing anything.
- 16 tests driving the real CLI through `PATH` stubs, so behavioural coverage does
  not require touching a live preference domain. CI runs on Linux and macOS.

**Known limitations**

- Not an Apple patch. Workarounds expire when 27.3 ships.
- The bug cannot be detected programmatically; the tool maps symptoms, it does not
  measure misrendering.
- Built from public reports. The author's machine runs macOS 26.6.2, where the bug
  does not reproduce, so version-specific behaviour is unverified locally.
