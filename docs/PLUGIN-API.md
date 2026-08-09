# The Lua side: what is possible, and what ElvUI does that this cannot

If you come from WoW addons, this is the page to read first. The gap between
"UI mod" in WoW and "UI mod" in LOTRO is large and it is architectural, not a
matter of effort.

## Why the gap exists

WoW's entire interface is written in Lua. An addon replaces real UI code, which
is why ElvUI can rebuild unit frames, action bars and nameplates from scratch.

LOTRO's interface is native C++. Lua was bolted on later as a **read-only
companion API**: the plugin talks to the client, the client decides what to
answer, and every method had to be written by hand on the C++ side before Lua
could call it. So the API covers what the developers chose to expose and nothing
more, and it deliberately excludes anything that could enable automation.

Practically: **you cannot replace LOTRO's UI, only add windows beside it and
repaint the existing one.** That is why MithrilUI is a skin *and* a plugin suite.
Restyling the built-in frames is the skin's job; new information displays are the
plugins' job. Neither can do the other's work.

## What the API gives you

| Area | Available | Notes |
|---|---|---|
| Your character | name, level, class, race | `Turbine.Gameplay.LocalPlayer.GetInstance()` |
| Your vitals | morale, power, and their maxima | change events exist for some |
| Your position | x, y, z (and instance id) | return shape has varied between updates |
| Your effects | name, icon, duration, start time, debuff flag | fields are individually optional |
| Your inventory | backpack size, items per slot | empty slots read as nil |
| Your skills | list and names | **not** reliable cooldown state |
| Quickslots | `Turbine.UI.Lotro.Quickslot` you create | the *user* can click it; your code cannot fire it |
| UI toolkit | windows, labels, controls, images, drag/drop | `Turbine.UI` and `Turbine.UI.Lotro` |
| Chat | read lines, write lines, register `/commands` | `Turbine.Shell` |
| Storage | per character / account / server | `Turbine.PluginData` |

## What it does not give you

- **Any other entity's state.** Target, fellowship member, raid member, monster:
  no morale, no power, no buffs, no position. This is the single biggest
  limitation and it rules out ElvUI-style unit frames outright.
- **Action bar control.** You cannot bind, re-bind, or trigger a skill.
- **Keybind interception.** If it appears in the Keybinding menu, Lua cannot fire it.
- **Raw key codes.** Only Actions the game already maps.
- **Reliable skill cooldowns.** MithrilUI originally planned a Cooldowns module
  and dropped it for this reason. Effect durations (BuffBars) work; skill
  recharge state does not, dependably.
- **The standard library.** Lua 5.1 with `math` and `string` only. No `os`, so
  no wall-clock time — durations come from `Turbine.Engine.GetGameTime()`.

## The capability probe

Because the API has moved between updates and some methods return nil depending
on character state, **nothing in MithrilUI calls Turbine directly.** Everything
goes through [`Core/Api.lua`](../plugins/MithrilUI/Core/Api.lua):

```lua
local function probe(name, fn, ...)
    if (Api.capabilities[name] == false) then return nil; end
    local ok, result = pcall(fn, ...);
    if (ok and result ~= nil) then
        Api.capabilities[name] = true;
        return result;
    end
    Api.capabilities[name] = false;   -- tried once, never again
    return nil;
end
```

A capability that fails is tried once, recorded, and never retried. Callers get
a clean `nil` instead of an error, and features whose data is missing switch
themselves off. The Databar drops unsupported segments from its layout on the
first tick rather than displaying "n/a" forever.

`/mithril diag` prints the whole table. That output is the right thing to attach
to a bug report — it says what your client actually answered, which is more
useful than a version number.

## Writing a module

```
plugins/MithrilUI/
  MyModule.plugin          <Package>MithrilUI.MyModule.Main</Package>
  MyModule/Main.lua
```

The author folder name is the first segment of the package path. `Core/` is
shared and imported by path:

```lua
import "MithrilUI.Core.Util";
import "MithrilUI.Core.Window";

local window = MithrilUI.Core.Window.New({
    module = "MyModule", width = 200, height = 40, x = 20, y = 20,
});
```

`Core.Window` gives you the flat frameless window, dragging, the shared lock
state, and position persistence. `Core.Bar` gives you a flat progress bar.
`Core.Settings` gives you a namespaced settings table that survives relogs.
`Core.ThemeColors` is **generated** from `themes/*.json` by `tools/gen_lua.py`,
so plugin colours and skin colours are the same numbers by construction.

Modules publish themselves into the `MithrilUI` global rather than returning a
value — that is the LOTRO convention, since `import` does not return modules.

Always define an unload handler; without it, reloading leaves orphaned windows:

```lua
Plugins["MithrilUI MyModule"].Unload = function() stop(); end
```

Check it before you launch:

```bash
python tools/check_plugins.py
```

This resolves every `<Package>` against the folder tree, resolves every `import`
against the files that exist, and — if `lupa` is installed — compiles each file
with a real Lua 5.1 parser. Without lupa it falls back to a keyword-balance
heuristic.

## Reference

- [LotRO API Reference](https://www.lotrointerface.com/wiki/LotRO_API_Reference)
- [Updated Lua Documentation](https://www.lotrointerface.com/downloads/info997-UpdatedLuaDocumentation.html)
- [LotroPluginExamples](https://github.com/shorinji/LotroPluginExamples) — small, readable working plugins
