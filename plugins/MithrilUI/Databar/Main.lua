--[[
    MithrilUI Databar -- one thin strip of the numbers you actually glance at.

    Segments are declarative: each one says how to fetch its value and whether
    the API supports it at all. A segment whose capability is missing removes
    itself from the layout on the first tick, so the bar never shows "n/a"
    forever on a client that cannot provide that field.

    Updates are polled, not evented, because most of these values have no
    change event. The poll runs at 4 Hz, which is invisible to the eye and
    invisible in the frame time.
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

local MODULE = "Databar";
local POLL_INTERVAL = 0.25;
local PADDING = 8;

local defaults = {
    enabled = true,
    segmentWidth = 96,
    height = 20,
    segments = {
        coords = true,
        bags = true,
        morale = true,
        power = true,
        level = false,
        session = true,
    },
};

local settings = Settings.For(MODULE, defaults);

local window = nil;
local labels = {};
local activeSegments = {};
local lastPoll = 0;
local sessionStart = 0;

-- -- segment definitions ---------------------------------------------------

--[[ Each segment: key, label prefix, and a Read() returning text or nil.
     Returning nil twice in a row retires the segment. ]]
local segments = {
    {
        key = "coords",
        Read = function()
            local pos = Api.GetPosition();
            if (pos == nil or pos.x == nil) then return nil; end
            return string.format("%.1f %.1f", pos.x, pos.y);
        end,
    },
    {
        key = "bags",
        Read = function()
            local free, total = Api.GetBagSpace();
            if (free == nil) then return nil; end
            return free .. "/" .. total;
        end,
    },
    {
        key = "morale",
        Read = function()
            local current, maximum = Api.GetMorale();
            if (current == nil or maximum == nil) then return nil; end
            return string.format("%d%%", math.floor(Util.Percent(current, maximum) * 100));
        end,
    },
    {
        key = "power",
        Read = function()
            local current, maximum = Api.GetPower();
            if (current == nil or maximum == nil) then return nil; end
            return string.format("%d%%", math.floor(Util.Percent(current, maximum) * 100));
        end,
    },
    {
        key = "level",
        Read = function()
            local level = Api.GetLevel();
            if (level == nil) then return nil; end
            return tostring(level);
        end,
    },
    {
        key = "session",
        Read = function()
            return Util.Duration(Util.Now() - sessionStart);
        end,
    },
};

local function labelFor(key)
    return L.Get("data." .. key);
end

-- -- layout ----------------------------------------------------------------

local function rebuild()
    for _, entry in pairs(labels) do
        pcall(function()
            entry.name:SetParent(nil);
            entry.value:SetParent(nil);
        end);
    end
    labels = {};

    local width = PADDING;
    for _, segment in ipairs(activeSegments) do
        local columnWidth = settings.segmentWidth;
        local nameLabel = UIWindow.Label(
            window, width, 0, columnWidth, settings.height,
            { text = labelFor(segment.key), color = "textDim" }
        );
        local valueLabel = UIWindow.Label(
            window, width, 0, columnWidth, settings.height,
            { text = "", color = "text",
              align = Turbine.UI.ContentAlignment.MiddleRight }
        );
        labels[segment.key] = { name = nameLabel, value = valueLabel };
        width = width + columnWidth + PADDING;
    end

    if (window ~= nil and window.MithrilResize ~= nil) then
        window.MithrilResize(math.max(width, 60), settings.height);
    end
end

--[[ First pass: ask every enabled segment once and keep the ones that answer.
     This is where an unsupported API silently drops out. ]]
local function discoverSegments()
    activeSegments = {};
    local dropped = {};
    for _, segment in ipairs(segments) do
        if (settings.segments[segment.key]) then
            local ok, value = pcall(segment.Read);
            if (ok and value ~= nil) then
                activeSegments[#activeSegments + 1] = segment;
            else
                dropped[#dropped + 1] = segment.key;
            end
        end
    end
    if (#dropped > 0) then
        Util.Print("Databar: no data for " .. table.concat(dropped, ", ")
            .. " on this client, hiding those. /mithril diag for detail.");
    end
end

local function poll()
    for _, segment in ipairs(activeSegments) do
        local entry = labels[segment.key];
        if (entry ~= nil) then
            local ok, value = pcall(segment.Read);
            entry.value:SetText((ok and value) or L.Get("data.unavailable"));
        end
    end
end

-- -- lifecycle -------------------------------------------------------------

local function start()
    sessionStart = Util.Now();

    window = UIWindow.New({
        module = MODULE,
        width = 400,
        height = settings.height,
        x = 20,
        y = 20,
        background = "panel",
    });

    discoverSegments();
    rebuild();
    poll();

    window:SetWantsUpdates(true);
    window.Update = function()
        local now = Util.Now();
        if (now - lastPoll < POLL_INTERVAL) then return; end
        lastPoll = now;
        poll();
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

--[[ Exposed so the Suite control panel can toggle segments at runtime. ]]
MithrilUI.Databar = {
    Rebuild = function()
        discoverSegments();
        rebuild();
        poll();
    end,
    Settings = settings,
    IsLoaded = function() return window ~= nil; end,
};

start();

Plugins["MithrilUI Databar"].Unload = function()
    stop();
end
