# Is this safe? Can it get my account banned?

Short answer: MithrilUI uses only the two customisation systems Standing Stone
Games built into the client and documents publicly. It reads no memory, sends no
packets, injects nothing into the game process, and automates no input. There is
nothing here for an anti-cheat system to object to, because nothing here talks to
the game except through the doors the developers opened.

That said, "trust me" is not a security argument. Here is exactly what the two
layers can and cannot do, so you can verify the claim rather than accept it.

## Layer 1: the skin

A skin is a folder containing `SkinDefinition.xml` and image files, placed in
`Documents\The Lord of the Rings Online\ui\skins\`. You switch it on inside the
game: **Options (Ctrl+O) → UI Settings → Current User Skin**.

The XML can do two things:

- `<Mapping ArtAssetID="..." FileName="..."/>` — draw one of the client's named
  art assets from your file instead of the built-in one.
- `<PanelFile ID="..."><Element ID="..." X Y Width Height/></PanelFile>` — move
  or resize a named piece of an interface panel.

That is the entire vocabulary. It is a skin, in the literal sense: it changes
what pixels get drawn. It cannot read game state, cannot make decisions, cannot
run code. The worst a broken skin can do is look wrong, and the fix is to pick a
different skin in the options panel.

## Layer 2: the Lua plugins

Plugins live in `Documents\The Lord of the Rings Online\Plugins\` and are managed
from the in-game Plugin Manager. They run in an embedded Lua 5.1 interpreter with
**only the `math` and `string` standard libraries loaded**. No `io`, no `os`, no
`package`, no `debug`, no sockets, no filesystem beyond the plugin data store.

The API surface is `Turbine.*`, and it is read-only by design. Plugins **cannot**:

- move your character, or issue any movement command
- use a skill, attack, or interact with an object or NPC
- press a key, click a button, or trigger anything that appears in the Keybinding menu
- read arbitrary world state: what is off screen, what is not targeted or grouped
- read or write game memory
- send or intercept network traffic
- talk to anything outside the game

This is not MithrilUI being polite. These capabilities are simply not in the API.
A plugin that wanted to bot could not, and the reason the API looks so restricted
is precisely that the developers designed it so plugins cannot be used to cheat.

**Correction.** An earlier version of this file claimed plugins cannot read a
target's morale or power at all. That is wrong: `Turbine.Gameplay` does expose
a target's morale, power and effects, and shipping plugins read them. The line
that actually matters for cheating is a different one, and it holds: plugins
can observe, but they cannot act. No movement, no skills, no keypresses.

## What MithrilUI specifically does

**Nothing from Layer 2.** MithrilUI is a skin and only a skin: XML plus TGA
files. It runs no code, reads no game state and has no plugin component. It
cannot do anything at runtime, because there is no runtime.

Layer 2 is documented above only so you can judge the plugins you install
alongside it.

## Things this project will not add

Not because they are hard, but because they are the line between a UI mod and a
cheat, and crossing it is what actually gets accounts banned in any game:

- external programs that read or write the game's memory
- packet inspection or injection
- input automation, macro playback, or key/click simulation from outside the game
- anything that reads data the API does not offer

Target health bars are fine, incidentally: the API does expose a target's
vitals and plugins legitimately read them. What should make you suspicious is
anything that *acts* for you, or that knows things nobody targeted: automatic
skill rotations, a radar of nearby entities, movement or gathering automation.
None of that is reachable through the Lua API, so anything offering it is
reaching around the API, and that is the category to stay away from.

## Practical notes

- Skins are read **once, at client startup**. Editing one while the game is
  running does nothing until you restart.
- Plugins reload live with `/plugins reload`.
- If a plugin throws a Lua error, it prints to your chat log and that plugin
  stops. Your character is unaffected. Unload it from the Plugin Manager.
- If a skin does not appear in the User Skins list, its XML failed to parse.
  Run `python tools/validate.py <skin folder>` to find out why.

## Sources

- [Custom UI Skinning in LOTRO](https://www.lotrointerface.com/index.php?p=ui_skinning_1) — the official skinning documentation, including the ArtAssetID dictionary.
- [LotRO API Reference](https://www.lotrointerface.com/wiki/LotRO_API_Reference) — the Lua API, and its stated limitations.
- [LoTROInterface downloads](https://www.lotrointerface.com/downloads/) — the community archive, actively updated; both skins and plugins have uploads from 2026.
