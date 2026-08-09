# MithrilUI

A minimal, clean interface overhaul for **The Lord of the Rings Online** — flat
panels, one hairline border, one accent colour. No wood grain, no gold filigree,
no parchment, no glass gloss.

Two layers, because LOTRO needs both: a **skin** that repaints and declutters the
game's own interface, and a **Lua plugin suite** that adds the displays the game
does not have. Plus the tooling to build, preview, validate and install all of it.

![MithrilUI Dark](docs/preview-dark.png)

*Mock-up composited from the actual generated TGA files. `mithril-ash` is the
same geometry with a different palette — [see it here](docs/preview-ash.png).*

---

## Is this allowed in 2026?

Yes. Both mechanisms are built into the client by Standing Stone Games and
switched on from the game's own options panel. The community archive at
[lotrointerface.com](https://www.lotrointerface.com/downloads/) is actively
updated — skins and plugins both have 2026 uploads.

MithrilUI reads no memory, sends no packets, injects nothing, and automates no
input. The Lua API physically cannot do those things: it runs Lua 5.1 with only
the `math` and `string` libraries and it is read-only by design, specifically so
plugins cannot be used to cheat. **[docs/SAFETY.md](docs/SAFETY.md)** spells out
exactly what is and is not touched, and how to verify it yourself.

## Honest scope: what ElvUI does that this cannot

Worth knowing before you install, because the difference is architectural rather
than a matter of effort. WoW's UI is written in Lua, so ElvUI can replace it.
LOTRO's UI is native C++ with a read-only Lua companion API bolted on.

**Not possible, by any addon, in LOTRO:**

- Unit frames for your target, fellowship or raid — the API exposes no other
  entity's morale, power or position at all
- Binding or triggering skills, or anything else in the Keybinding menu
- Reliable skill cooldown state

**What you get instead:** the built-in frames stripped of ornament and moved
where you want them (skin), plus your own vitals, effects and data readouts as
clean windows (plugins). [docs/PLUGIN-API.md](docs/PLUGIN-API.md) has the full
capability table.

## Quick start

Python 3.9+, nothing else to install.

```bash
git clone https://github.com/Felix-Helleckes/MithrilUI.git
cd MithrilUI
python tools/build.py
python tools/install.py
```

Restart the client, then **Options (Ctrl+O) → UI Settings → Misc → Current User
Skin → MithrilUI Dark**. For plugins, use *Manage Plugins* on the character
selection screen and set *automatically load for*, or `/plugins refresh` then
`/plugins load MithrilUI` in game.

Prefer not to build? Grab the archives from
[Releases](https://github.com/Felix-Helleckes/MithrilUI/releases) — they unzip
straight into `ui\skins\` and `Plugins\`.

Full walkthrough and troubleshooting in [docs/INSTALL.md](docs/INSTALL.md).

## What is in it

### Skin

137 generated assets replacing the panel bodies, 9-slice frames, title bars,
buttons, tabs, chat background, list selections and the auto-attack indicator.
Selected rows get a solid accent bar down the left edge, which is what keeps
selection readable once the heavy blue gradient is gone.

The `declutter` profile additionally removes the store button, the XP-bar gloss
and its decorative end caps, and pins the toolbar to the bottom centre.

### Plugins

| Module | What it does |
|---|---|
| **MithrilUI** | `/mithril` command, control panel, shared window lock. Load first. |
| **Databar** | One thin strip: coordinates, free bag slots, morale %, power %, session time. Segments the client cannot supply hide themselves. |
| **Vitals** | Flat morale and power bars with a low-morale colour shift. Yours only — the API offers no one else's. |
| **BuffBars** | Effects as an icon grid, buffs and debuffs on separate rows, sorted by remaining time, countdown under each icon. |

Windows load locked and click straight through to the world. `/mithril lock` to
move them; positions save per character.

## Tools

The point of the tooling is that nothing is hand-drawn or hand-edited. A theme is
one JSON file that drives the skin art *and* the plugin colours.

| Command | Purpose |
|---|---|
| `tools/build.py` | Themes + recipes + layout → a ready skin folder |
| `tools/preview.py` | PNG mock-up or contact sheet from the real TGAs, no game restart |
| `tools/validate.py` | Catches the silent failures: bad XML, missing files, wrong sizes, unresolved templates |
| `tools/check_plugins.py` | Resolves every `<Package>` and `import`; compiles the Lua with a real 5.1 parser if `lupa` is present |
| `tools/extract_ids.py` | Mines panel/element IDs out of any installed skin — the only practical way to find them |
| `tools/install.py` | Copies or symlinks into the LOTRO folder; `--uninstall`, `--dry-run` |
| `tools/gen_lua.py` | Emits the shared palette as Lua so skin and plugins cannot drift apart |
| `tools/package.py` | Release zips in the single-root-folder shape lotrointerface.com requires |

```bash
python tools/build.py --profile declutter --resolution 2560x1440
python tools/build.py --theme mithril-ash
python tools/build.py --all
python tools/preview.py --sheet
```

## Making it yours

Copy a file in `themes/`, change the hex values, `python tools/build.py --theme
<your-id>`. That is the whole workflow — every asset is drawn from a recipe
(`solid`, `panel`, `nine_corner`, `button`, `tab`, `selection`, `ring`, …), so a
new palette is a rebuild, not a redraw.

Adding an asset means one entry in `skin/assets.json` with the size from the
[official ArtAssetID dictionary](https://www.lotrointerface.com/index.php?p=ui_skinning_2).
Adding a look means one function in `tools/gen_art.py`.

## Status

**v0.1.0 — the skin and the tooling are verified; the plugins are not yet
in-game tested.**

Verified here: all 137 assets generate and pass the validator, the generated XML
parses, and all 11 Lua files compile under a real Lua 5.1 parser. Not verified:
how the plugins behave inside a running client. That is why every game API call
goes through a capability probe that fails soft — see
[docs/PLUGIN-API.md](docs/PLUGIN-API.md) — and why `/mithril diag` exists.

If a module does nothing on your client, `/mithril diag` output is the useful
thing to put in an issue.

Known gaps, in rough order of interest:

- Layout modules beyond the toolbar (bags, character panel, chat placement)
- The vitals layout module needs measured numbers and ships disabled
- Flat replacement icons for the toolbar pictograms
- Per-character theme switching from `/mithril config`

## Credits

Built on the community's documentation, not on its art — every pixel here is
generated. Thanks to the authors keeping LOTRO skinning alive, in particular
[Adra's JRR Skins Collection](https://www.lotrointerface.com/downloads/info581-jrrskinscollection-atributetomiddleearth.html),
whose structure was the reference for how modern `PanelFile` layout actually
works, and to [LoTROInterface](https://www.lotrointerface.com) for hosting the
API and skinning documentation.

Not affiliated with or endorsed by Standing Stone Games or Middle-earth
Enterprises. *The Lord of the Rings Online* is a trademark of its respective
owners.

## Licence

[MIT](LICENSE).
