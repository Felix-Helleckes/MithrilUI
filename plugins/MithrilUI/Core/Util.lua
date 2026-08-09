--[[
    MithrilUI.Core.Util -- small helpers shared by every module.

    LOTRO's Lua is 5.1 with only the math and string libraries loaded: no io,
    no os, no os.time. Anything time-related has to come from Turbine, and
    anything table-related has to be written out by hand.
]]

import "Turbine";

MithrilUI = MithrilUI or {};
MithrilUI.Core = MithrilUI.Core or {};

local Util = {};

Util.VERSION = "0.1.0";

-- -- numbers -------------------------------------------------------------

function Util.Clamp(value, low, high)
    if (value < low) then return low; end
    if (value > high) then return high; end
    return value;
end

function Util.Round(value, decimals)
    local factor = 10 ^ (decimals or 0);
    return math.floor(value * factor + 0.5) / factor;
end

--[[ 1234567 -> "1.23m". Keeps data rows narrow. ]]
function Util.ShortNumber(value)
    if (value == nil) then return "-"; end
    local absolute = math.abs(value);
    if (absolute >= 1000000) then
        return string.format("%.2fm", value / 1000000);
    elseif (absolute >= 10000) then
        return string.format("%.1fk", value / 1000);
    end
    return tostring(math.floor(value));
end

--[[ Seconds -> "1:05" or "12s". Durations under a minute stay compact. ]]
function Util.Duration(seconds)
    if (seconds == nil or seconds < 0) then return ""; end
    seconds = math.floor(seconds + 0.5);
    if (seconds >= 3600) then
        return string.format("%d:%02d:%02d",
            math.floor(seconds / 3600),
            math.floor((seconds % 3600) / 60),
            seconds % 60);
    elseif (seconds >= 60) then
        return string.format("%d:%02d", math.floor(seconds / 60), seconds % 60);
    end
    return seconds .. "s";
end

function Util.Percent(current, maximum)
    if (current == nil or maximum == nil or maximum <= 0) then return 0; end
    return Util.Clamp(current / maximum, 0, 1);
end

-- -- time ----------------------------------------------------------------

--[[ Seconds since the client started. `os` is not available, so this is the
     only clock we get. Fine for durations, useless for wall-clock time. ]]
function Util.Now()
    local ok, value = pcall(function()
        return Turbine.Engine.GetGameTime();
    end);
    if (ok and value ~= nil) then return value; end
    return 0;
end

-- -- tables --------------------------------------------------------------

function Util.Copy(source)
    if (type(source) ~= "table") then return source; end
    local out = {};
    for key, value in pairs(source) do
        out[key] = Util.Copy(value);
    end
    return out;
end

--[[ Fill in missing keys from `defaults` without clobbering existing ones.
     Used when a saved settings file predates a new option. ]]
function Util.ApplyDefaults(target, defaults)
    target = target or {};
    for key, value in pairs(defaults) do
        if (target[key] == nil) then
            target[key] = Util.Copy(value);
        elseif (type(value) == "table" and type(target[key]) == "table") then
            Util.ApplyDefaults(target[key], value);
        end
    end
    return target;
end

function Util.Count(t)
    local n = 0;
    for _ in pairs(t) do n = n + 1; end
    return n;
end

-- -- strings -------------------------------------------------------------

function Util.Split(text, separator)
    separator = separator or " ";
    local parts = {};
    for piece in string.gmatch(text, "([^" .. separator .. "]+)") do
        parts[#parts + 1] = piece;
    end
    return parts;
end

function Util.Trim(text)
    return (string.gsub(text or "", "^%s*(.-)%s*$", "%1"));
end

-- -- chat output ---------------------------------------------------------

local PREFIX = "MithrilUI: ";

function Util.Print(message)
    pcall(function() Turbine.Shell.WriteLine(PREFIX .. tostring(message)); end);
end

function Util.PrintRaw(message)
    pcall(function() Turbine.Shell.WriteLine(tostring(message)); end);
end

MithrilUI.Core.Util = Util;
