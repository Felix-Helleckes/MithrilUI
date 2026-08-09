# Installing MithrilUI

Needs Python 3.9+ and nothing else. No `pip install`, no build tools. (`lupa` is
optional and only sharpens the plugin linter.)

## 1. Build

```bash
git clone https://github.com/Felix-Helleckes/MithrilUI.git
cd MithrilUI
python tools/build.py
```

That writes `dist/skins/MithrilUI/`. For the version that also strips the store
button and the XP-bar gloss, pass your real resolution:

```bash
python tools/build.py --profile declutter --resolution 2560x1440
```

## 2. Install

```bash
python tools/install.py
```

It finds your LOTRO folder (including OneDrive-redirected Documents), copies
every built skin into `ui\skins\`, and the plugin suite into `Plugins\`.

Check first if you like:

```bash
python tools/install.py --dry-run
```

If auto-detection fails, point at it: `python tools/install.py --game-dir "D:/LOTRO"`.

Doing it by hand is fine too — copy `dist/skins/MithrilUI` into
`Documents\The Lord of the Rings Online\ui\skins\` and `plugins/MithrilUI` into
`Documents\The Lord of the Rings Online\Plugins\`.

## 3. Turn it on

**Skin** — restart the client first; skins are only read at startup.
Then **Options (Ctrl+O) → UI Settings → Current User Skin → MithrilUI Dark → Accept**.

**Plugins** — no restart needed. In game:

```
/plugins refresh
/plugins load MithrilUI
```

Then load whichever displays you want from the Plugin Manager: *MithrilUI
Databar*, *MithrilUI Vitals*, *MithrilUI BuffBars*. Load `MithrilUI` itself
first — it owns the `/mithril` command and the shared window lock.

## 4. Arrange it

```
/mithril lock      unlock windows, drag them, run again to lock
/mithril reset     everything back to default positions
/mithril config    small panel showing which modules are live
/mithril diag      what your client's API actually supports
```

Windows are locked on load and click straight through to the world, so they never
get in your way until you unlock them deliberately. Positions are saved per
character.

## Changing how it looks

Two themes ship: `mithril-dark` (cool silver-blue) and `mithril-ash` (warm grey
and bronze).

```bash
python tools/build.py --theme mithril-ash
```

For your own, copy a file in `themes/`, change the hex values, build with
`--theme <your-id>`. That single file drives the skin art *and* the plugin
colours — `tools/build.py` regenerates `plugins/MithrilUI/Core/ThemeColors.lua`
from the same numbers on every build.

Preview without launching the game:

```bash
python tools/preview.py            # mock window built from the real TGAs
python tools/preview.py --sheet    # every asset on one contact sheet
```

## Development loop

```bash
python tools/install.py --link
```

Symlinks instead of copying, so an edit in the repo is live in the game folder.
Needs Developer Mode or an elevated shell on Windows. Plugins then reload with
`/plugins reload`; skin changes still need a client restart.

## Removing it

```bash
python tools/install.py --uninstall
```

Or delete the `MithrilUI*` folders from `ui\skins\` and `Plugins\` and switch the
skin back to Default in the options panel.

## When something does not work

**Skin missing from the User Skins list.** Its XML failed to parse — the client
gives no error. Run `python tools/validate.py dist/skins/MithrilUI`.

**Skin changes not showing.** Restart the client. There is no live reload for skins.

**A plugin window is empty.** Run `/mithril diag`. If the capability it needs is
listed as unavailable, that client does not expose the data and the module has
correctly switched itself off.

**Lua error in chat.** Unload that plugin from the Plugin Manager and open an
issue with the error text and your `/mithril diag` output.
