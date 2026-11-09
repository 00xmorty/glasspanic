# glasspanic

Triage for the macOS 27.2 "Liquid Glass" render bug: blank dialogs, invisible menus,
dead menu-bar clicks, and third-party status panels that refuse to open.

One command, no sudo, no install, no telemetry. It tells you which symptom you have,
what actually helps for that symptom, and what to do when nothing does.

```sh
./glasspanic
```

```
glasspanic 0.1.0 — Liquid Glass render-bug triage
Mode: read-only (no change unless --apply / --revert / --nudge)

SYSTEM
  platform        Darwin 27.2 (build 26B123)
  symptom map for macOS 27.2 (build 26B1xx)
  version match   yes — this machine is on 27.2

VIEW SETTINGS (read from preferences)
  Reduce Transparency                unset (system default, key never written)
  Reduce Motion                      0
  ...
```

## Why this exists

macOS 27.2 shipped a broken Liquid Glass compositing layer. The symptoms look like
four unrelated disasters, so the internet answers each one separately and people
conclude their Mac is dying. They reboot, they buy a cleaner app, they reinstall
Office. None of that is the problem.

The bug is reported as fixed in 27.3 (beta 1, 2026-11-04). Until you can update,
`glasspanic` maps your symptom to the workaround that is actually reported to work
for it, and says how confident that mapping is.

## Symptoms it recognises

| id | What you see |
|---|---|
| `blank_dialog` | Save/close dialogs render empty grey and ignore clicks; text appears only after you take a screenshot |
| `menus_vanish` | Switching apps leaves the menu bar empty even though it is drawn |
| `menubar_clicks` | Clicks on the menu bar never reach `MenuBarAgent` |
| `third_party_panel` | Vendor status panels (surge-style dashboards) will not open |

Each one prints what it looks like, the first thing to try, and the public evidence
it is based on. Sources are listed at the bottom of this file.

## Usage

```sh
./glasspanic                 # symptom map + current view settings
./glasspanic --json          # same data, machine-readable
./glasspanic --apply         # store Reduce Transparency = on, verify read-back
./glasspanic --revert        # store Reduce Transparency = off, verify read-back
./glasspanic --nudge         # restart SystemUIServer / MenuBarAgent (asks first)
./glasspanic --apply --print # show the command, change nothing
```

`--nudge` needs `--yes` when it is not attached to a terminal. Without it the tool
refuses rather than guessing that a script meant to flash your UI.

Exit codes: `0` ok, `2` usage error, `3` a preference write could not be verified.

## Safety

- **No sudo.** Nothing here escalates.
- **No deletion.** No files, caches, or applications are removed.
- **No third-party app is quit.** `--nudge` touches only `SystemUIServer` and
  `MenuBarAgent`, only if they are running, and only with `--yes` or a prompt.
- **No network.** Zero outbound calls, zero telemetry, zero analytics.
- **One preference, explicitly.** `--apply`/`--revert` write exactly one key:
  `com.apple.universalaccess reduceTransparency`. They read it back and fail loudly
  if the value did not stick.
- **Nothing is claimed.** A stored preference is not proof the running UI applied it,
  and the tool says so every time.

## Limitations

- **This is not an Apple patch.** It cannot fix the compositing bug. Every workaround
  here expires when 27.3 lands. If 27.3 does not help, the answer is an Apple bug
  report, not another tool.
- **It cannot verify the bug on your behalf.** It reads settings and maps symptoms.
  It does not detect whether Liquid Glass is currently misrendering — there is no
  public API for that.
- **`blank_dialog`, `menus_vanish`, and `third_party_panel` have no reliable local
  fix.** For those the honest answer is "redraw, then wait for 27.3". The tool says
  that instead of selling you a fix.
- **Unreadable preferences are reported as `unset`, never guessed.** A key that was
  never written is not the same as a key that is off, and the output keeps them apart.
- **The `com.apple.universalaccess` domain can be read but is not always the domain
  the live UI uses.** Where a second location exists it is probed too, and a missing
  key is shown as missing.
- **Tested against stubs, not against a 27.2 machine.** The author's host is macOS
  26.6.2, where the bug does not reproduce. The symptom map is built from public
  reports, not from local reproduction. Treat version-specific claims with that in mind.

## Install

Single file, no dependencies:

```sh
curl -fsSL -o glasspanic https://github.com/00xmorty/glasspanic/releases/latest/download/glasspanic
chmod +x glasspanic
./glasspanic
```

Or clone and run:

```sh
git clone https://github.com/00xmorty/glasspanic
cd glasspanic && ./glasspanic
```

Requires `zsh` (default on macOS) and macOS 13 or newer for the preference probes.
On non-macOS hosts the doctor still runs and reports settings as `unsupported`.

## Tests

```sh
python3 -m unittest discover -s tests -v
```

The suite drives the real CLI through `PATH` stubs for `defaults`, `sw_vers`,
`uname`, `pgrep`, and `killall`, so it never reads or writes your actual
preferences and runs identically on Linux CI.

## Evidence

- Apple Support Communities: blank grey dialogs, 2026-11-06 —
  https://discussions.apple.com/thread/256389850
- MacRumors: "Solution to disappearing menus in macOS 27.2" —
  https://forums.macrumors.com/threads/solution-to-disappearing-menus-in-macos-27-2.2493017/
- GitHub `jizhi0v0/macos27-beta-issues` issue #35 (FB25347429) —
  https://github.com/jizhi0v0/macos27-beta-issues
- Surge knowledge base, dashboard crash (FB25184160, fix deferred to 27.3) —
  https://kb.nssurge.com/surge-knowledge-base/faq/mac-dashboard-crash

## License

MIT — see [LICENSE](LICENSE).
