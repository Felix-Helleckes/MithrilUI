--[[
    MithrilUI Vitals -- flat morale and power bars for your own character.

    Scope note, because it is the single most common misunderstanding about
    LOTRO plugins: this shows YOUR vitals only. The Lua API does not expose the
    morale or power of a target, a fellowship member, or another player, so a
    plugin cannot build ElvUI-style unit frames for them. Cleaning up the
    built-in fellowship and target frames is a job for the skin layer, not for
    Lua. See docs/PLUGIN-API.md.

    Uses change events when the client fires them and falls back to polling
    when it does not.
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
import "MithrilUI.Core.Bar";

local Util = MithrilUI.Core.Util;
local Api = MithrilUI.Core.Api;
local L = MithrilUI.Core.Locale;
local Settings = MithrilUI.Core.Settings;
local UIWindow = MithrilUI.Core.Window;
local Bar = MithrilUI.Core.Bar;

local MODULE = "Vitals";
local POLL_INTERVAL = 0.2;

local defaults = {
    width = 220,
    barHeight = 14,
    gap = 3,
    showHeader = true,
    showPower = true,
    lowMoraleThreshold = 0.25,
};

local settings = Settings.For(MODULE, defaults);

local window = nil;
local header = nil;
local moraleBar = nil;
local powerBar = nil;
local lastPoll = 0;
local usingEvents = false;

local function refresh()
    local morale, maxMorale = Api.GetMorale();
    if (moraleBar ~= nil) then
        if (morale == nil) then
            moraleBar.SetText(L.Get("data.unavailable"));
        else
            moraleBar.SetValueColored(morale, maxMorale, settings.lowMoraleThreshold);
        end
    end

    if (powerBar ~= nil) then
        local power, maxPower = Api.GetPower();
        if (power == nil) then
            powerBar.SetText(L.Get("data.unavailable"));
        else
            powerBar.SetValue(power, maxPower);
        end
    end
end

local function buildHeader()
    if (not settings.showHeader) then return nil; end

    local name = Api.GetName();
    local level = Api.GetLevel();
    local className = Api.GetClassName();

    local parts = {};
    if (name ~= nil) then parts[#parts + 1] = name; end
    if (level ~= nil) then parts[#parts + 1] = L.Get("data.level") .. " " .. level; end
    if (className ~= nil) then parts[#parts + 1] = className; end
    if (#parts == 0) then return nil; end

    return UIWindow.Label(window, 4, 0, settings.width - 8, 16, {
        text = table.concat(parts, "  ·  "),
        color = "textDim",
    });
end

local function start()
    local barCount = settings.showPower and 2 or 1;
    local headerHeight = settings.showHeader and 18 or 0;
    local height = headerHeight
        + barCount * settings.barHeight
        + (barCount - 1) * settings.gap
        + 6;

    window = UIWindow.New({
        module = MODULE,
        width = settings.width,
        height = height,
        x = 20,
        y = 60,
        background = "panel",
    });

    header = buildHeader();

    local y = headerHeight + 3;
    moraleBar = Bar.New(window, 4, y, {
        width = settings.width - 8,
        height = settings.barHeight,
        color = "good",
    });
    y = y + settings.barHeight + settings.gap;

    if (settings.showPower) then
        powerBar = Bar.New(window, 4, y, {
            width = settings.width - 8,
            height = settings.barHeight,
            color = "accent",
        });
    end

    refresh();

    -- Prefer events; poll only if the client did not give us any.
    usingEvents = Api.OnVitalsChanged(refresh);
    if (not usingEvents) then
        window:SetWantsUpdates(true);
        window.Update = function()
            local now = Util.Now();
            if (now - lastPoll < POLL_INTERVAL) then return; end
            lastPoll = now;
            refresh();
        end
    end
end

local function stop()
    Settings.Save(true);
    if (window ~= nil) then
        window:SetWantsUpdates(false);
        if (window.MithrilDispose ~= nil) then window.MithrilDispose(); end
        window = nil;
    end
end

MithrilUI.Vitals = {
    Refresh = refresh,
    Settings = settings,
    UsingEvents = function() return usingEvents; end,
    IsLoaded = function() return window ~= nil; end,
};

start();

Plugins["MithrilUI Vitals"].Unload = function()
    stop();
end
