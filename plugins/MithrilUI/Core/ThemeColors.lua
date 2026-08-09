-- GENERATED FILE - do not edit by hand.
-- Source: themes/mithril-dark.json
-- Rebuild with: python tools/build.py
--
-- Values are 0..1 components ready for Turbine.UI.Color(a, r, g, b).

import "Turbine";
import "Turbine.UI";

-- LOTRO plugins share one global table per apartment, so modules
-- publish themselves into a namespace rather than returning a value.
MithrilUI = MithrilUI or {};
MithrilUI.Core = MithrilUI.Core or {};

local ThemeColors = {};

ThemeColors.id = "mithril-dark";
ThemeColors.name = "MithrilUI Dark";

ThemeColors.raw = {
    panel = { a = 0.902, r = 0.055, g = 0.067, b = 0.086 },
    panelAlt = { a = 0.902, r = 0.078, g = 0.098, b = 0.133 },
    header = { a = 0.949, r = 0.039, g = 0.051, b = 0.071 },
    border = { a = 1.000, r = 0.165, g = 0.196, b = 0.247 },
    borderBright = { a = 1.000, r = 0.239, g = 0.278, b = 0.341 },
    accent = { a = 1.000, r = 0.498, g = 0.698, b = 0.851 },
    accentDim = { a = 1.000, r = 0.290, g = 0.435, b = 0.549 },
    text = { a = 1.000, r = 0.843, g = 0.871, b = 0.910 },
    textDim = { a = 1.000, r = 0.553, g = 0.592, b = 0.651 },
    button = { a = 0.949, r = 0.102, g = 0.125, b = 0.161 },
    buttonHover = { a = 1.000, r = 0.137, g = 0.173, b = 0.220 },
    buttonDown = { a = 1.000, r = 0.043, g = 0.055, b = 0.075 },
    good = { a = 1.000, r = 0.498, g = 0.851, b = 0.635 },
    bad = { a = 1.000, r = 0.851, g = 0.502, b = 0.498 },
    shadow = { a = 1.000, r = 0.000, g = 0.000, b = 0.000 },
};

-- Turbine.UI.Color instances, built once at load.
ThemeColors.color = {};
for name, c in pairs(ThemeColors.raw) do
    ThemeColors.color[name] = Turbine.UI.Color(c.a, c.r, c.g, c.b);
end

-- Same hue, custom alpha. Handy for hover states and washes.
function ThemeColors.Alpha(name, alpha)
    local c = ThemeColors.raw[name];
    if (c == nil) then return Turbine.UI.Color(1, 1, 0, 1); end
    return Turbine.UI.Color(alpha, c.r, c.g, c.b);
end

MithrilUI.Core.ThemeColors = ThemeColors;
