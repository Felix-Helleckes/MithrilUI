# How LOTRO skinning works, and how MithrilUI uses it

Everything here was verified against the official documentation and against real
skins in the wild. Where something is uncertain, it says so.

## The file the game reads

One folder per skin under `Documents\The Lord of the Rings Online\ui\skins\`,
each containing `SkinDefinition.xml` plus its images. The root element is `<opt>`:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<opt>
<SkinName Name="MithrilUI Dark"></SkinName>

<Mapping ArtAssetID="basepanel_topleft" FileName="art\panels\basepanel_topleft.tga" />

<PanelFile ID="ID_UISkin_Toolbar">
  <Element ID="ToolbarField" X="750" Y="1030" Width="420" Height="50">
    <Element ID="Toolbar_WebstoreButton" X="0" Y="0" Width="1" Height="1"></Element>
  </Element>
</PanelFile>
</opt>
```

Two mechanisms, and it is worth being precise about the difference:

**`<Mapping>` replaces art.** `ArtAssetID` is a name from the client's own asset
table — you cannot invent one. The official list, with the exact pixel dimensions
the game expects, is on
[the skinning documentation, page 2](https://www.lotrointerface.com/index.php?p=ui_skinning_2).
`FileName` is a path relative to the skin folder. Images are TGA (32-bit RGBA).

**`<PanelFile>` / `<Element>` moves parts of a panel.** This is the half the
original documentation never covered and the half that makes real UI overhauls
possible. Each `Element` needs all four of `X`, `Y`, `Width`, `Height`.

## The three rules that cost the most time

**1. There is no "hide" attribute.** To remove something, shrink it:
`Width="1" Height="1"`. That is the community-standard technique and it is what
MithrilUI's toolbar module uses.

**2. Declaring a child forces you to declare its parent's geometry.** You cannot
hide one toolbar button without also stating where the whole toolbar goes. This
is why layout modules are resolution-dependent while art mappings are not, and
why MithrilUI ships layout as opt-in.

**3. XML comments cannot contain `--`.** A double hyphen inside `<!-- -->` makes
the file malformed, and the client's entire response to malformed XML is to leave
your skin out of the list with no error anywhere. `tools/gen_skin.py` fails the
build on this so you find out in one second instead of one evening.

Also worth knowing: **skins are read once at client startup.** Editing a live
skin does nothing until you restart. There is no `/reloadui`.

## Finding element IDs

There is no complete published list. The practical method is to read skins that
already touch the panel you care about:

```bash
python tools/extract_ids.py "C:/Users/you/Documents/The Lord of the Rings Online/ui/skins" --kind tree
```

That prints every `PanelFile` with its `Element` children, from every skin you
have installed. Narrow it down:

```bash
python tools/extract_ids.py <path> --panel ID_UISkin_Toolbar
```

`docs/reference-element-ids.txt` in this repo is such a dump (693 IDs), used by
the validator to flag likely typos. It is a sample, not the full universe — an ID
missing from it may still be perfectly valid.

An unknown or misspelled ID is ignored by the client. It never crashes; you just
do not get the effect you wanted.

## How MithrilUI is built

Nothing in `dist/` is committed. The skin is generated:

```
themes/mithril-dark.json     colours, opacities, border width
skin/assets.json             ArtAssetID -> size + recipe + module
skin/layout/*.xml            templated PanelFile fragments
profiles/*.json              which modules, which theme, which resolution
        |
        v  python tools/build.py
dist/skins/MithrilUI/        SkinDefinition.xml + art/*.tga
```

`tools/gen_art.py` draws every asset from a recipe — `solid`, `panel`,
`nine_corner`, `nine_edge`, `header`, `button`, `tab`, `selection`, `ring`,
`divider`, `dot`, `close_button`, `hidden`. No file is hand-drawn, so changing
the whole palette means editing one JSON file and rebuilding.

To add an asset, add an entry to `skin/assets.json` with the size from the
official dictionary. To add a look, add a recipe function to `gen_art.py`.

## Tuning a layout module

Layout fragments are templates. `{{ }}` holds an arithmetic expression evaluated
against your profile's variables, and `<!-- @if flag -->` blocks are included
only when the flag is true:

```xml
<Element ID="ToolbarField"
         X="{{ (screenWidth - toolbarWidth) / 2 }}"
         Y="{{ screenHeight - toolbarHeight }}"
         Width="{{ toolbarWidth }}" Height="{{ toolbarHeight }}">
```

`screenWidth` and `screenHeight` come from the profile's `resolution`; every
numeric entry in `options` becomes a variable, and every boolean becomes a flag.
The expression evaluator handles arithmetic plus `min`, `max`, `round`, `int`,
`abs` — it is not `eval`, so a fragment cannot run arbitrary code.

Build for your actual resolution:

```bash
python tools/build.py --profile declutter --resolution 2560x1440
```

**The vitals module needs numbers only you can measure.** The stock size of the
vitals panel is not published, and the defaults in `profiles/declutter.json` are
an educated guess, which is why that module ships disabled. To tune it: enable
it, build, restart, look, adjust `vitalsX/Y/Width/Height`, repeat. Use
`extract_ids.py` against a skin that already handles vitals to see what values
someone else arrived at.

## Checking your work

```bash
python tools/validate.py dist/skins/MithrilUI
```

Checks the XML parses, that there is exactly one `SkinName`, that no ArtAssetID
is mapped twice, that every referenced file exists and is a readable 32-bit TGA
of the size the game expects, that every `Element` has all four coordinates and
no unresolved `{{ }}` left in them, and that no art is left unreferenced.

```bash
python tools/preview.py --sheet
```

Renders every generated asset onto one PNG contact sheet, and without `--sheet`
composites a mock window from the real TGAs. Faster than restarting the client
when you are iterating on colours.
