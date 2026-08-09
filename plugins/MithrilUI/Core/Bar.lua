--[[
    MithrilUI.Core.Bar -- a flat progress bar.

    Two stacked controls: a track and a fill whose width is set from a 0..1
    ratio. No gradients, no end caps, no glass overlay. An optional label sits
    on top and never intercepts the mouse.
]]

import "Turbine";
import "Turbine.UI";

MithrilUI = MithrilUI or {};
MithrilUI.Core = MithrilUI.Core or {};

import "MithrilUI.Core.Util";
import "MithrilUI.Core.ThemeColors";

local Util = MithrilUI.Core.Util;
local Colors = MithrilUI.Core.ThemeColors;

local Bar = {};

--[[ options = {
        width, height,
        color     = "accent",     -- fill colour role
        track     = "panelAlt",   -- background colour role
        label     = true,         -- draw text over the bar
        align     = ...,          -- label alignment
     }
]]
function Bar.New(parent, x, y, options)
    options = options or {};
    local width = options.width or 160;
    local height = options.height or 12;

    local track = Turbine.UI.Control();
    track:SetParent(parent);
    track:SetPosition(x, y);
    track:SetSize(width, height);
    track:SetMouseVisible(false);
    if (Colors ~= nil) then
        track:SetBackColor(Colors.Alpha(options.track or "panelAlt", 0.75));
    end

    local fill = Turbine.UI.Control();
    fill:SetParent(track);
    fill:SetPosition(0, 0);
    fill:SetSize(0, height);
    fill:SetMouseVisible(false);
    if (Colors ~= nil) then
        fill:SetBackColor(Colors.color[options.color or "accent"]);
    end

    local label = nil;
    if (options.label ~= false) then
        label = Turbine.UI.Label();
        label:SetParent(track);
        label:SetPosition(0, 0);
        label:SetSize(width, height);
        label:SetMouseVisible(false);
        pcall(function()
            label:SetFont(options.font or Turbine.UI.Lotro.Font.Verdana12);
            label:SetTextAlignment(options.align or Turbine.UI.ContentAlignment.MiddleCenter);
            label:SetFontStyle(Turbine.UI.FontStyle.Outline);
        end);
        if (Colors ~= nil) then
            label:SetForeColor(Colors.color.text);
            pcall(function() label:SetOutlineColor(Colors.Alpha("shadow", 0.9)); end);
        end
    end

    local bar = {
        track = track,
        fill = fill,
        label = label,
        width = width,
        height = height,
        colorRole = options.color or "accent",
    };

    --[[ ratio is 0..1. Anything outside gets clamped rather than drawing a
         fill wider than its track. ]]
    function bar.SetRatio(ratio)
        local clamped = Util.Clamp(ratio or 0, 0, 1);
        fill:SetSize(math.floor(bar.width * clamped + 0.5), bar.height);
    end

    function bar.SetValue(current, maximum)
        bar.SetRatio(Util.Percent(current, maximum));
        if (label ~= nil and options.autoText ~= false) then
            if (current == nil or maximum == nil) then
                label:SetText("");
            else
                label:SetText(Util.ShortNumber(current) .. " / " .. Util.ShortNumber(maximum));
            end
        end
    end

    function bar.SetText(text)
        if (label ~= nil) then label:SetText(text or ""); end
    end

    function bar.SetColor(role)
        bar.colorRole = role;
        if (Colors ~= nil and Colors.color[role] ~= nil) then
            fill:SetBackColor(Colors.color[role]);
        end
    end

    --[[ Tint the fill by how full it is. Used for morale: healthy stays
         accent-coloured, low turns red, which is the one place where colour
         carries information rather than decoration. ]]
    function bar.SetValueColored(current, maximum, lowThreshold)
        bar.SetValue(current, maximum);
        local ratio = Util.Percent(current, maximum);
        if (ratio <= (lowThreshold or 0.25)) then
            bar.SetColor("bad");
        else
            bar.SetColor(bar.baseColor or "accent");
        end
    end

    function bar.Resize(newWidth, newHeight)
        bar.width = newWidth;
        bar.height = newHeight or bar.height;
        track:SetSize(bar.width, bar.height);
        if (label ~= nil) then label:SetSize(bar.width, bar.height); end
    end

    function bar.SetVisible(visible)
        track:SetVisible(visible and true or false);
    end

    bar.baseColor = options.color or "accent";
    return bar;
end

MithrilUI.Core.Bar = Bar;
