# Security

## What this tool touches

`glasspanic` is a local diagnostic CLI. It has a deliberately small blast radius:

- Reads individual preference keys with `defaults read`.
- Writes exactly one preference key, and only when you ask for it:
  `com.apple.universalaccess reduceTransparency` (`--apply` / `--revert`).
- Restarts `SystemUIServer` and `MenuBarAgent` only under `--nudge`, only when they
  are running, and only after `--yes` or an interactive confirmation.

It does not use `sudo`, does not delete files, does not uninstall anything, does not
quit third-party applications, and makes no network requests.

## Reporting a vulnerability

Open a private security advisory at
https://github.com/00xmorty/glasspanic/security/advisories/new
or email mustafa@neurabytelabs.com.

Please do not open a public issue for anything that could let the tool modify state
outside the single preference key above.

## Out of scope

- The macOS rendering bug itself. This tool cannot fix it; report that to Apple.
- Any behaviour that requires elevated privileges. If a patch needs `sudo`, it is the
  wrong patch for this project.
- Preference domains other than the documented ones. `--apply` writes one key on
  purpose, so a feature request to "clean up all accessibility settings" will be
  declined.
