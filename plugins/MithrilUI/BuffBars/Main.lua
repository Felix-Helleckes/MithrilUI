--[[
    MithrilUI BuffBars -- your effects as a plain icon grid with timers.

    The default effect display is small, unsorted and mixed. This separates
    buffs from debuffs into two rows, sorts by remaining time so the thing
    about to fall off sits at a predictable end, and puts a readable countdown
    under each icon.

    Effect fields are all optional in the API: an effect may report no icon, no
    duration, or neither. Every one of those cases has to render as something
    sensible rather than as a Lua error.
]]

import "Turbine";
import "Turbine.UI";
import "Turbine.Gameplay";

import "MithrilUI.Core.Util";
import "MithrilUI.Core.Api";
import "MithrilUI.Core.Locale";
import "MithrilUI.Core.Settings";
import "MithrilUI.Core.ThemeColors";
import "MithrilUI.Core.Window";

local Util = MithrilUI.Core.Util;
local Api = MithrilUI.Core.Api;
local L = MithrilUI.Core.Locale;
local Settings = MithrilUI.Core.Settings;
local Colors = MithrilUI.Core.ThemeColors;
local UIWindow = MithrilUI.Core.Window;

local MODULE = "BuffBars";
local POLL_INTERVAL = 0.25;

local defaults = {
    iconSize = 32;
    spacing = 3,
    perRow = 10,
    showTimers = true,
    separateDebuffs = true,
    hidePermanent = false,
};

local settings = Settings.For(MODULE, defaults);

local window = nil;
local slots = {};          -- reused icon controls, never recreated per tick
local lastPoll = 0;
local lastSignature = "";

-- -- slot pool -------------------------------------------------------------

--[[ Recreating controls every tick is how a plugin becomes a stutter. Build a
     pool once and only change what is on it. ]]
local function acquireSlot(index)
    if (slots[index] ~= nil) then return slots[index]; end

    local icon = Turbine.UI.Control();
    icon:SetParent(window);
    icon:SetSize(settings.iconSize, settings.iconSize);
    icon:SetMouseVisible(false);
    if (Colors ~= nil) then
        icon:SetBackColor(Colors.Alpha("panelAlt", 0.6));
    end

    local timer = UIWindow.Label(
        window, 0, 0, settings.iconSize, 12,
        { text = "", color = "text",
          align = Turbine.UI.ContentAlignment.MiddleCenter }
    );

    slots[index] = { icon = icon, timer = timer, inUse = false };
    return slots[index];
end

local function hideFrom(index)
    for i = index, #slots do
        slots[i].icon:SetVisible(false);
        slots[i].timer:SetVisible(false);
        slots[i].inUse = false;
    end
end

-- -- data ------------------------------------------------------------------

local function remaining(effect)
    if (effect.duration == nil or effect.duration <= 0) then return nil; end
    if (effect.startTime == nil) then return effect.duration; end
    local left = (effect.startTime + effect.duration) - Util.Now();
    if (left < 0) then return 0; end
    return left;
end

local function collect()
    local effects = Api.GetEffects();
    if (effects == nil) then return nil, nil; end

    local buffs, debuffs = {}, {};
    for _, effect in ipairs(effects) do
        effect.remaining = remaining(effect);
        local permanent = (effect.remaining == nil);
        if (not (settings.hidePermanent and permanent)) then
            if (settings.separateDebuffs and effect.isDebuff) then
                debuffs[#debuffs + 1] = effect;
            else
                buffs[#buffs + 1] = effect;
            end
        end
    end

    -- Shortest remaining first; permanent effects sink to the end.
    local function byRemaining(a, b)
        if (a.remaining == nil and b.remaining == nil) then
            return (a.name or "") < (b.name or "");
        end
        if (a.remaining == nil) then return false; end
        if (b.remaining == nil) then return true; end
        return a.remaining < b.remaining;
    end
    table.sort(buffs, byRemaining);
    table.sort(debuffs, byRemaining);

    return buffs, debuffs;
end

-- -- rendering -------------------------------------------------------------

local function drawRow(list, startIndex, y, isDebuff)
    local index = startIndex;
    local column = 0;
    local row = 0;

    for _, effect in ipairs(list) do
        local slot = acquireSlot(index);
        local x = column * (settings.iconSize + settings.spacing);
        local slotY = y + row * (settings.iconSize + 14 + settings.spacing);

        slot.icon:SetPosition(x, slotY);
        slot.icon:SetSize(settings.iconSize, settings.iconSize);
        slot.icon:SetVisible(true);
        slot.inUse = true;

        if (effect.icon ~= nil) then
            pcall(function() slot.icon:SetBackground(effect.icon); end);
        elseif (Colors ~= nil) then
            -- No icon available: a flat accent block still marks the slot.
            slot.icon:SetBackColor(Colors.Alpha(isDebuff and "bad" or "accent", 0.45));
        end

        if (settings.showTimers) then
            slot.timer:SetPosition(x, slotY + settings.iconSize);
            slot.timer:SetSize(settings.iconSize, 12);
            slot.timer:SetVisible(true);
            slot.timer:SetText(effect.remaining and Util.Duration(effect.remaining) or "");
        else
            slot.timer:SetVisible(false);
        end

        index = index + 1;
        column = column + 1;
        if (column >= settings.perRow) then
            column = 0;
            row = row + 1;
        end
    end

    local rowsUsed = row + (column > 0 and 1 or 0);
    return index, rowsUsed;
end

local function refresh()
    local buffs, debuffs = collect();
    if (buffs == nil) then
        hideFrom(1);
        return;
    end

    -- Skip the redraw when nothing actually changed except the clock.
    local signature = #buffs .. ":" .. #debuffs;
    local rowHeight = settings.iconSize + 14 + settings.spacing;

    local nextIndex, buffRows = drawRow(buffs, 1, 0, false);
    local debuffRows = 0;
    if (settings.separateDebuffs and #debuffs > 0) then
        nextIndex, debuffRows = drawRow(debuffs, nextIndex, buffRows * rowHeight + 6, true);
    end
    hideFrom(nextIndex);

    if (signature ~= lastSignature and window ~= nil and window.MithrilResize ~= nil) then
        lastSignature = signature;
        local totalRows = math.max(1, buffRows + debuffRows);
        local width = math.min(#buffs + #debuffs, settings.perRow)
            * (settings.iconSize + settings.spacing);
        window.MithrilResize(
            math.max(width, settings.iconSize + settings.spacing),
            totalRows * rowHeight + 6
        );
    end
end

-- -- lifecycle -------------------------------------------------------------

local function start()
    window = UIWindow.New({
        module = MODULE,
        width = settings.perRow * (settings.iconSize + settings.spacing),
        height = settings.iconSize + 14,
        x = 20,
        y = 140,
        background = "panel",
    });

    if (Api.GetEffects() == nil) then
        Util.Print("BuffBars: this client does not expose effect data, the window will stay empty. "
            .. "/mithril diag for detail.");
    end

    refresh();
    Api.OnEffectsChanged(refresh);

    -- Timers tick down even when the effect list itself has not changed, so
    -- poll regardless of whether the events attached.
    window:SetWantsUpdates(true);
    window.Update = function()
        local now = Util.Now();
        if (now - lastPoll < POLL_INTERVAL) then return; end
        lastPoll = now;
        refresh();
    end
end

local function stop()
    Settings.Save(true);
    if (window ~= nil) then
        window:SetWantsUpdates(false);
        if (window.MithrilDispose ~= nil) then window.MithrilDispose(); end
        window = nil;
    end
    slots = {};
end

MithrilUI.BuffBars = {
    Refresh = refresh,
    Settings = settings,
    IsLoaded = function() return window ~= nil; end,
};

start();

Plugins["MithrilUI BuffBars"].Unload = function()
    stop();
end
