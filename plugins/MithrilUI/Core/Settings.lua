--[[
    MithrilUI.Core.Settings -- per-character persistence.

    Turbine.PluginData is the only storage plugins get. It is a key/value store
    scoped to Character, Account or Server, and it silently refuses anything it
    cannot serialise (functions, userdata, cycles), so settings tables must stay
    plain data.

    Every module gets its own namespace inside one saved blob, which keeps the
    number of save calls down and makes `/mithril reset` a single operation.
]]

import "Turbine";

MithrilUI = MithrilUI or {};
MithrilUI.Core = MithrilUI.Core or {};

import "MithrilUI.Core.Util";

local Util = MithrilUI.Core.Util;
local Settings = {};

local STORAGE_KEY = "MithrilUISettings";

local data = nil;
local dirty = false;

local function scope()
    -- Character scope keeps a hunter's layout off a minstrel's screen.
    local ok, value = pcall(function() return Turbine.DataScope.Character; end);
    if (ok and value ~= nil) then return value; end
    return 1;
end

--[[ Load once per session. A missing or corrupt blob resets to empty rather
     than taking the plugin down with it. ]]
function Settings.Load()
    if (data ~= nil) then return data; end

    local ok, loaded = pcall(function()
        return Turbine.PluginData.Load(scope(), STORAGE_KEY);
    end);

    if (ok and type(loaded) == "table") then
        data = loaded;
    else
        data = {};
        if (not ok) then
            Util.Print("could not read saved settings, starting fresh");
        end
    end
    return data;
end

--[[ Get a module's settings table, filling in any defaults it has grown. ]]
function Settings.For(moduleName, defaults)
    local root = Settings.Load();
    root[moduleName] = Util.ApplyDefaults(root[moduleName] or {}, defaults or {});
    return root[moduleName];
end

function Settings.MarkDirty()
    dirty = true;
end

--[[ Turbine.PluginData writes the table out as Lua source and reads it back
     with a strict parser. Anything it cannot represent produces a file that
     fails to load on the next session, and the only symptom is a syntax error
     naming a line number in a file you never wrote.

     So the table is rebuilt from scratch before saving, keeping only string
     keys and plain scalar values. Numeric keys, nils, functions and anything
     exotic are dropped rather than risking an unreadable save. ]]
local function sanitize(value, depth)
    depth = depth or 0;
    if (depth > 8) then return nil; end

    local kind = type(value);
    if (kind == "string" or kind == "boolean") then
        return value;
    end
    if (kind == "number") then
        -- Inf and NaN both serialise to something the reader rejects.
        if (value ~= value or value == math.huge or value == -math.huge) then
            return nil;
        end
        return value;
    end
    if (kind ~= "table") then
        return nil;
    end

    local out = {};
    local count = 0;
    for key, item in pairs(value) do
        if (type(key) == "string" and string.find(key, "^[%a_][%w_]*$") ~= nil) then
            local cleaned = sanitize(item, depth + 1);
            if (cleaned ~= nil) then
                out[key] = cleaned;
                count = count + 1;
            end
        end
    end
    if (count == 0) then return nil; end
    return out;
end

--[[ Write to disk. Call on unload and after deliberate changes, not on every
     drag event -- saving is not free. ]]
function Settings.Save(force)
    if (data == nil) then return false; end
    if (not dirty and not force) then return false; end

    local payload = sanitize(data) or {};
    local ok, err = pcall(function()
        Turbine.PluginData.Save(scope(), STORAGE_KEY, payload);
    end);

    if (ok) then
        dirty = false;
        return true;
    end
    Util.Print("could not save settings: " .. tostring(err));
    return false;
end

function Settings.ResetModule(moduleName)
    local root = Settings.Load();
    root[moduleName] = nil;
    dirty = true;
end

function Settings.ResetAll()
    data = {};
    dirty = true;
    Settings.Save(true);
end

--[[ Remember where a window ended up. Stored per module so modules can be
     loaded and unloaded independently. ]]
function Settings.SaveWindowPosition(moduleName, x, y)
    local moduleSettings = Settings.For(moduleName, {});
    moduleSettings.window = moduleSettings.window or {};
    moduleSettings.window.x = x;
    moduleSettings.window.y = y;
    dirty = true;
end

function Settings.GetWindowPosition(moduleName)
    local moduleSettings = Settings.For(moduleName, {});
    if (moduleSettings.window == nil) then return nil, nil; end
    return moduleSettings.window.x, moduleSettings.window.y;
end

MithrilUI.Core.Settings = Settings;
