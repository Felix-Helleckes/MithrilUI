# MithrilUI

A minimal, clean interface overhaul for **The Lord of the Rings Online** — flat
panels, one hairline border, one accent colour. No wood grain, no gold filigree,
no parchment, no glass gloss.

Pure skin: it repaints and declutters the game's own interface and nothing else.
No Lua plugins, no extra windows, no runtime code. Every asset is generated from
a theme file, so a whole retheme is one JSON edit and a rebuild.

![MithrilUI Dark](docs/preview-dark.png)

*Mock-up composited from the actual generated TGA files. `mithril-ash` is the
same geometry with a different palette — [see it here](docs/preview-ash.png).*

---

## Is this allowed in 2026?

Yes. Skinning is built into the client by Standing Stone Games and switched on
from the game's own options panel. The community archive at
[lotrointerface.com](https://www.lotrointerface.com/downloads/) is actively
updated, with skin uploads through 2026.

A skin is XML plus images. It replaces named art assets and repositions named
interface elements — that is the entire vocabulary. It cannot read game state,
cannot run code, and cannot do anything at all beyond changing which pixels get
drawn. **[docs/SAFETY.md](docs/SAFETY.md)** has the detail.

## Honest scope: what ElvUI does that this cannot

Worth knowing before you install, because the difference is architectural rather
than a matter of effort. WoW's UI is written in Lua, so ElvUI can rebuild it.
LOTRO's UI is native C++ and only its *artwork and element geometry* are
exposed to skins.

**Not possible for any LOTRO skin:**

- Rebuilding unit frames, action bars or nameplates as new widgets
- Adding behaviour: no drag-to-resize, no new buttons, no scripting
- Anything conditional — a skin has no logic, only a fixed mapping

**What you get instead:** every ornate frame, carved plate, gold filigree and
glass overlay in the interface replaced with flat colour or removed outright,
while the layout stays exactly where the game's own UI-layout tool (Ctrl+\)
put it.

## Quick start

Python 3.9+, nothing else to install.

```bash
git clone https://github.com/Felix-Helleckes/MithrilUI.git
cd MithrilUI
python tools/build.py
python tools/install.py
```

Restart the client — skins are only read at startup — then **Options (Ctrl+O) →
UI Settings → Misc → Current User Skin → MithrilUI Dark**.

Prefer not to build? Grab the archive from
[Releases](https://github.com/Felix-Helleckes/MithrilUI/releases) and unzip it
straight into `ui\skins\`.

Full walkthrough and troubleshooting in [docs/INSTALL.md](docs/INSTALL.md).

## What is in it

**~2100 replaced assets.** 137 are hand-tuned against the documented ArtAssetID
dictionary — panel bodies, 9-slice frames, title bars, buttons, tabs, chat,
list selections. The rest come from the **sweep**: an ordered set of name
patterns over the full 2622-entry asset list, because the official dictionary
dates from 2007 and covers barely 5% of what the modern client draws.

The sweep's governing rule is that removing ornament means making it invisible,
not painting a dark rectangle over it:

| Group | Treatment |
|---|---|
| HUD ornament (vitals plates, gambit frames) | cleared |
| Window bodies, backdrops | 72% flat fill |
| Buttons, slots, tabs | 55% translucent plate |
| Hover / pressed / selection | light accent wash |
| Icons, quest difficulty, item rarity, class pips | **never touched** (597 assets) |
| Everything else — frames, corners, caps, filigree | cleared |

The `declutter` profile additionally removes the store button and the XP-bar
gloss, and pins the toolbar to the bottom centre. Note that pinning it means
Ctrl+\ can no longer move it, which is why it is not the default.

## Tools

The point of the tooling is that nothing is hand-drawn or hand-edited. A theme is
one JSON file that drives every asset in the skin.

| Command | Purpose |
|---|---|
| `tools/build.py` | Themes + recipes + layout → a ready skin folder |
| `tools/preview.py` | PNG mock-up or contact sheet from the real TGAs, no game restart |
| `tools/validate.py` | Catches the silent failures: bad XML, missing files, wrong sizes, unresolved templates |
| `tools/extract_ids.py` | Mines panel/element IDs out of any installed skin — the only practical way to find them |
| `tools/install.py` | Copies or symlinks into the LOTRO folder; `--uninstall`, `--dry-run` |
| `tools/package.py` | Release zips in the single-root-folder shape lotrointerface.com requires |
| `tools/debug_lookup.py` | Turns a colour picked out of a screenshot back into the ArtAssetID that drew it |

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

## Diagnosing a skin

Most ArtAssetIDs say nothing about where they appear, and LOTRO reports a bad
skin by silently leaving it out of the list. Two diagnostic profiles exist so
"which asset is that?" is a lookup rather than a guessing game.

```bash
python tools/build.py --profile debug    # colour by rule category
python tools/build.py --profile ident    # unique colour per asset + legend
```

Pick the skin in game, screenshot the element you are wondering about, then:

```bash
python tools/debug_lookup.py "#a1b2c3"
```

Anything that keeps its original look under `ident` is drawn by the client and
cannot be reached from a skin at all — which is itself the answer to a whole
class of question.

## Status

**v0.2.0 — in-game tested, still being tuned.**

The tooling is solid: every asset generates, all builds pass the validator, and
the generated XML parses. The sweep's pattern rules are the part still settling
— they were built from in-game evidence and each round of feedback moves an
asset group between "clear it", "fill it" and "leave it alone".

Known gaps, in rough order of interest:

- Layout modules beyond the toolbar (bags, character panel, chat placement)
- The vitals layout module needs measured numbers and ships disabled
- Flat replacement icons for the toolbar pictograms
- Sweep rules for the world map and minimap are unverified

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
