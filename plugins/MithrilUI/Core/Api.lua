--[[
    MithrilUI.Core.Api -- a guarded layer over the Turbine game API.

    Why this exists
    ---------------
    LOTRO's Lua API is deliberately narrow and it has changed shape across
    updates: methods appear, get renamed, or exist but return nil for some
    character states. A plugin that calls player:GetWallet() directly and
    guesses wrong throws a Lua error into the chat log on every frame.

    So nothing in MithrilUI touches the Turbine API directly. Everything goes
    through a probe: each capability is tried once inside pcall, the result is
    remembered, and callers get either a real value or a clean nil. A feature
    whose API is missing quietly switches itself off instead of spamming errors.

    `/mithril diag` prints the probe table, which is also the fastest way to
    tell someone what their client actually supports.

    What this file will never do
    ----------------------------
    Read no memory, send no packets, trigger no skills, press no keys. The API
    does not offer those and MithrilUI does not want them. See docs/SAFETY.md.
]]

import "Turbine";
import "Turbine.Gameplay";
import "Turbine.UI";

MithrilUI = MithrilUI or {};
MithrilUI.Core = MithrilUI.Core or {};

local Api = {};

-- capability name -> true (works) / false (tried, unavailable)
Api.capabilities = {};
Api.errors = {};

local player = nil;

--[[ Try `fn`, remember whether it worked, never let it escape. ]]
local function probe(name, fn, ...)
    if (Api.capabilities[name] == false) then
        return nil;
    end

    local ok, result = pcall(fn, ...);
    if (ok and result ~= nil) then
        Api.capabilities[name] = true;
        return result;
    end

    -- Record the first failure only; after that the capability stays off.
    if (Api.capabilities[name] == nil) then
        Api.capabilities[name] = false;
        if (not ok) then
            Api.errors[name] = tostring(result);
        else
            Api.errors[name] = "returned nil";
        end
    end
    return nil;
end

Api.Probe = probe;

--[[ The local player object. Everything else hangs off this. ]]
function Api.GetPlayer()
    if (player ~= nil) then
        return player;
    end
    player = probe("player", function()
        return Turbine.Gameplay.LocalPlayer.GetInstance();
    end);
    return player;
end

-- -- identity ------------------------------------------------------------

function Api.GetName()
    local p = Api.GetPlayer();
    if (p == nil) then return nil; end
    return probe("name", function() return p:GetName(); end);
end

function Api.GetLevel()
    local p = Api.GetPlayer();
    if (p == nil) then return nil; end
    return probe("level", function() return p:GetLevel(); end);
end

function Api.GetClassName()
    local p = Api.GetPlayer();
    if (p == nil) then return nil; end
    return probe("class", function()
        return Turbine.Gameplay.Class.GetName(p:GetClass());
    end);
end

-- -- vitals --------------------------------------------------------------

function Api.GetMorale()
    local p = Api.GetPlayer();
    if (p == nil) then return nil, nil; end
    local current = probe("morale", function() return p:GetMorale(); end);
    local maximum = probe("maxMorale", function() return p:GetMaxMorale(); end);
    return current, maximum;
end

function Api.GetPower()
    local p = Api.GetPlayer();
    if (p == nil) then return nil, nil; end
    local current = probe("power", function() return p:GetPower(); end);
    local maximum = probe("maxPower", function() return p:GetMaxPower(); end);
    return current, maximum;
end

--[[ Hook a vitals event if the client fires one. Returns true when the
     handler was attached, so callers know whether they must poll instead. ]]
function Api.OnVitalsChanged(handler)
    local p = Api.GetPlayer();
    if (p == nil) then return false; end

    local attached = false;
    local events = { "MoraleChanged", "MaxMoraleChanged", "PowerChanged", "MaxPowerChanged" };
    for _, name in ipairs(events) do
        local ok = pcall(function()
            local previous = p[name];
            p[name] = function(sender, args)
                if (previous ~= nil) then pcall(previous, sender, args); end
                pcall(handler);
            end
            attached = true;
        end);
        Api.capabilities["event." .. name] = ok and attached;
    end
    return attached;
end

-- -- position ------------------------------------------------------------

--[[ GetPosition's return shape has varied. Handle both the four-value form
     (instance, x, y, z) and the three-value form. ]]
function Api.GetPosition()
    local p = Api.GetPlayer();
    if (p == nil) then return nil; end

    local ok, a, b, c, d = pcall(function() return p:GetPosition(); end);
    if (not ok or a == nil) then
        if (Api.capabilities["position"] == nil) then
            Api.capabilities["position"] = false;
            Api.errors["position"] = ok and "returned nil" or tostring(a);
        end
        return nil;
    end

    Api.capabilities["position"] = true;
    if (d ~= nil) then
        return { instance = a, x = b, y = c, z = d };
    end
    return { instance = nil, x = a, y = b, z = c };
end

-- -- inventory -----------------------------------------------------------

--[[ Free / total backpack slots. Empty slots read back as nil. ]]
function Api.GetBagSpace()
    local p = Api.GetPlayer();
    if (p == nil) then return nil, nil; end

    local backpack = probe("backpack", function() return p:GetBackpack(); end);
    if (backpack == nil) then return nil, nil; end

    local size = probe("backpackSize", function() return backpack:GetSize(); end);
    if (size == nil) then return nil, nil; end

    local used = 0;
    local counted = pcall(function()
        for slot = 1, size do
            if (backpack:GetItem(slot) ~= nil) then
                used = used + 1;
            end
        end
    end);
    if (not counted) then
        Api.capabilities["backpackItems"] = false;
        return nil, size;
    end
    Api.capabilities["backpackItems"] = true;
    return size - used, size;
end

-- -- effects -------------------------------------------------------------

--[[ Snapshot of current buffs and debuffs.

     Every field is optional: some effects report no duration, some no icon.
     Callers must cope with nil rather than assume. ]]
function Api.GetEffects()
    local p = Api.GetPlayer();
    if (p == nil) then return nil; end

    local list = probe("effects", function() return p:GetEffects(); end);
    if (list == nil) then return nil; end

    local count = probe("effectCount", function() return list:GetCount(); end);
    if (count == nil) then return nil; end

    local out = {};
    for index = 1, count do
        local ok, effect = pcall(function() return list:Get(index); end);
        if (ok and effect ~= nil) then
            local entry = { index = index };
            pcall(function() entry.name = effect:GetName(); end);
            pcall(function() entry.icon = effect:GetIcon(); end);
            pcall(function() entry.duration = effect:GetDuration(); end);
            pcall(function() entry.startTime = effect:GetStartTime(); end);
            pcall(function() entry.isDebuff = effect:IsDebuff(); end);
            pcall(function() entry.isCurable = effect:IsCurable(); end);
            pcall(function() entry.description = effect:GetDescription(); end);
            out[#out + 1] = entry;
        end
    end
    Api.capabilities["effectDetails"] = (#out > 0) or (count == 0);
    return out;
end

--[[ Attach to effect add/remove if available. Returns true on success. ]]
function Api.OnEffectsChanged(handler)
    local p = Api.GetPlayer();
    if (p == nil) then return false; end

    local list = probe("effects", function() return p:GetEffects(); end);
    if (list == nil) then return false; end

    local attached = false;
    for _, name in ipairs({ "EffectAdded", "EffectRemoved", "EffectsCleared" }) do
        local ok = pcall(function()
            local previous = list[name];
            list[name] = function(sender, args)
                if (previous ~= nil) then pcall(previous, sender, args); end
                pcall(handler);
            end
            attached = true;
        end);
        Api.capabilities["event." .. name] = ok and attached;
    end
    return attached;
end

-- -- screen --------------------------------------------------------------

function Api.GetScreenSize()
    local width = probe("screenWidth", function() return Turbine.UI.Display.GetWidth(); end);
    local height = probe("screenHeight", function() return Turbine.UI.Display.GetHeight(); end);
    if (width == nil or height == nil) then
        return 1920, 1080;  -- a sane guess beats a crash
    end
    return width, height;
end

-- -- diagnostics ---------------------------------------------------------

--[[ Sorted capability report. This is what `/mithril diag` prints, and what
     to paste into a bug report. ]]
function Api.Report()
    local names = {};
    for name in pairs(Api.capabilities) do
        names[#names + 1] = name;
    end
    table.sort(names);

    local lines = {};
    local available, missing = 0, 0;
    for _, name in ipairs(names) do
        if (Api.capabilities[name]) then
            available = available + 1;
            lines[#lines + 1] = "  ok   " .. name;
        else
            missing = missing + 1;
            local reason = Api.errors[name];
            lines[#lines + 1] = "  --   " .. name .. (reason and ("  (" .. reason .. ")") or "");
        end
    end
    return lines, available, missing;
end

--[[ Force everything to be re-tested, e.g. after a game update. ]]
function Api.Reset()
    Api.capabilities = {};
    Api.errors = {};
    player = nil;
end

MithrilUI.Core.Api = Api;
