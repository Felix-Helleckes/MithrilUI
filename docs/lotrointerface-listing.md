# lotrointerface upload sheet

Copy-paste material for the submission form. Category: **Graphical
Modifications (Skins)**. Archive: `MithrilUI-Skin-Dark-1.0.0.zip`.

---

## Name

MithrilUI

## Short description (the line that shows in listings)

A minimal, flat interface skin. No wood, no gold filigree, no parchment.

---

## Description

**MithrilUI strips the ornament out of the LOTRO interface and leaves the
information.** Flat near-black panels, one hairline border, one cool
silver-blue accent. The carved plates, the end caps, the glass sheen and the
gold filigree are gone; what tells you something stays exactly where it was.

Nothing is repositioned by default, so **Ctrl+\ still moves everything** the
way it always did.

### What changes

- ~1800 replaced art assets across panels, journals, vendors, the auction
  house, chat, bags and the toolbar
- Flat dark window bodies with a single thin border, instead of carved frames
- Selected rows get a solid accent bar down the left edge, so selection stays
  obvious once the heavy blue gradient is gone
- The toolbar plate is dark and flat; its glass sheen is removed
- The XP bar gets flat colours: accent for normal gain, green for rested,
  dim for suppressed
- Chat sits on a proper dark background, which the game itself does not offer

### A bonus you will notice the first time you rearrange your UI

Open the layout editor (Esc, or Ctrl+\) and every movable panel picks up a
hatched alignment overlay with a bright border marking its true bounds. The
panel you are dragging turns green. It vanishes the moment you close the
editor.

This works because the client only draws that art while the editor is open,
so the skin does not need any logic, which is fortunate, because skins do not
have any.

### What is deliberately left alone

Icons, class resource pips, gambit symbols, quest difficulty markers, item
rarity colours, checkboxes, scrollbar handles, loading bars, the map arrow.
866 assets in total. Anything that carries information rather than decoration
stays untouched.

### Please report anything that disappears

About 280 assets are cleared by a catch-all rule, because their names give no
clue what they draw. `note_avatar` turned out to be the world map's player
arrow. `gambit_orangestar` is a Warden's gambit builder. Both were found by
someone noticing they were missing, and both are fixed.

If something you need vanishes, post it here or open an issue on GitHub. The
fix is one line, and the asset almost certainly has a name nobody would guess.

### Install

1. Unzip into `Documents\The Lord of the Rings Online\ui\skins\`
2. **Restart the client** — skins are only read at startup
3. Options (Ctrl+O) → UI Settings → scroll to **Misc** → Current User Skin →
   MithrilUI Dark → Accept

If it does not appear in the list, the XML failed to parse and the client says
nothing about it. The repo ships a validator that tells you why.

### Tested on

Warden, 2560x1440. Other classes are protected by rule and look correct in the
manifest but have not been seen in game.

### Source

Every asset is generated from a theme file by a Python toolchain, no
hand-drawn art. Recipes, rules and the full build are on GitHub:
https://github.com/Felix-Helleckes/MithrilUI

Want a different palette? Copy one JSON file, change the hex values, rebuild.
A second theme (warm grey and bronze) ships as an example.

### Credits

Thanks to Adra, whose JRR Skins Collection was the reference for how modern
panel layout actually works, and to LoTROInterface for hosting the skinning
documentation that made any of this possible.

Not affiliated with Standing Stone Games or Middle-earth Enterprises.
