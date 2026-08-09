--[[
    MithrilUI.Core.Window -- the frameless, draggable window every module uses.

    Turbine.UI.Lotro.Window gives you the game's ornate frame, which is exactly
    what this project exists to get away from. So modules build on plain
    Turbine.UI.Window and paint their own background: one flat fill, one
    hairline border, nothing else.

    Behaviour that would otherwise be reimplemented three times lives here:
    dragging, click-through when locked, position persistence, and a lock state
    shared by every window at once.
]]

import "Turbine";
import "Turbine.UI";

MithrilUI = MithrilUI or {};
MithrilUI.Core = MithrilUI.Core or {};

import "MithrilUI.Core.Util";
import "MithrilUI.Core.Settings";
import "MithrilUI.Core.ThemeColors";

local Util = MithrilUI.Core.Util;
local Settings = MithrilUI.Core.Settings;
local Colors = MithrilUI.Core.ThemeColors;

local Window = {};

-- Every window registers here so lock/reset can reach all of them at once.
local registry = {};
local locked = true;

--[[ Create a MithrilUI window.

     options = {
        module   = "Databar",          -- settings namespace, required
        width    = 240, height = 24,
        x = 40, y = 40,                -- default position, overridden by saved
        title    = nil,                -- optional, drawn as a small label
        border   = true,
        background = "panel",          -- theme colour role
     }
]]
function Window.New(options)
    options = options or {};
    local moduleName = options.module or "MithrilUI";

    local window = Turbine.UI.Window();
    window:SetSize(options.width or 240, options.height or 24);

    local savedX, savedY = Settings.GetWindowPosition(moduleName);
    window:SetPosition(savedX or options.x or 40, savedY or options.y or 40);

    window:SetVisible(true);
    window:SetOpacity(1);
    window:SetZOrder(options.zOrder or 0);

    -- The flat background. Turbine.UI.Window has no border concept, so the
    -- border is a second control sized to match, drawn behind the content.
    local backgroundRole = options.background or "panel";
    if (Colors ~= nil and Colors.color[backgroundRole] ~= nil) then
        window:SetBackColor(Colors.color[backgroundRole]);
    end

    local border = nil;
    if (options.border ~= false and Colors ~= nil) then
        border = Turbine.UI.Control();
        border:SetParent(window);
        border:SetPosition(0, 0);
        border:SetSize(window:GetWidth(), window:GetHeight());
        border:SetBackColor(Colors.Alpha("border", 0));
        border:SetMouseVisible(false);
        border:SetZOrder(-1);
    end

    -- -- dragging -------------------------------------------------------

    local dragging = false;
    local dragX, dragY = 0, 0;

    window.MouseDown = function(sender, args)
        if (locked) then return; end
        dragging = true;
        dragX, dragY = args.X, args.Y;
    end

    window.MouseMove = function(sender, args)
        if (not dragging) then return; end
        local x, y = window:GetPosition();
        window:SetPosition(x + (args.X - dragX), y + (args.Y - dragY));
    end

    window.MouseUp = function(sender, args)
        if (not dragging) then return; end
        dragging = false;
        local x, y = window:GetPosition();
        Settings.SaveWindowPosition(moduleName, x, y);
        Settings.MarkDirty();
    end

    -- -- lock handling --------------------------------------------------

    --[[ When locked the window must not eat clicks meant for the world
         behind it. SetMouseVisible(false) is what makes that happen. ]]
    local function applyLock()
        window:SetMouseVisible(not locked);
        if (Colors == nil) then return; end
        if (locked) then
            window:SetBackColor(Colors.color[backgroundRole]);
            if (border ~= nil) then border:SetBackColor(Colors.Alpha("border", 0)); end
        else
            -- Unlocked windows show their outline so you can see what you grab.
            window:SetBackColor(Colors.Alpha(backgroundRole, 0.95));
            if (border ~= nil) then border:SetBackColor(Colors.Alpha("accent", 0.55)); end
        end
    end

    local entry = {
        control = window,
        module = moduleName,
        border = border,
        applyLock = applyLock,
        defaultX = options.x or 40,
        defaultY = options.y or 40,
    };
    registry[#registry + 1] = entry;
    applyLock();

    -- -- helpers exposed on the window ----------------------------------

    window.MithrilResize = function(width, height)
        window:SetSize(width, height);
        if (border ~= nil) then border:SetSize(width, height); end
    end

    window.MithrilDispose = function()
        for index, item in ipairs(registry) do
            if (item.control == window) then
                table.remove(registry, index);
                break;
            end
        end
        window:SetVisible(false);
        window:SetParent(nil);
    end

    return window;
end

-- -- global lock state ----------------------------------------------------

function Window.SetLocked(value)
    locked = value and true or false;
    for _, entry in ipairs(registry) do
        pcall(entry.applyLock);
    end
    Settings.MarkDirty();
    return locked;
end

function Window.ToggleLock()
    return Window.SetLocked(not locked);
end

function Window.IsLocked()
    return locked;
end

--[[ Send every registered window back to the position its module asked for. ]]
function Window.ResetPositions()
    for _, entry in ipairs(registry) do
        pcall(function()
            entry.control:SetPosition(entry.defaultX, entry.defaultY);
            Settings.SaveWindowPosition(entry.module, entry.defaultX, entry.defaultY);
        end);
    end
    Settings.MarkDirty();
    Settings.Save(true);
end

function Window.Count()
    return #registry;
end

-- -- label helper ---------------------------------------------------------

--[[ A label styled to match the skin. Modules build rows out of these rather
     than configuring fonts and colours in five places. ]]
function Window.Label(parent, x, y, width, height, options)
    options = options or {};
    local label = Turbine.UI.Label();
    label:SetParent(parent);
    label:SetPosition(x, y);
    label:SetSize(width, height);
    label:SetMouseVisible(false);

    pcall(function()
        label:SetFont(options.font or Turbine.UI.Lotro.Font.Verdana12);
    end);
    pcall(function()
        label:SetTextAlignment(options.align or Turbine.UI.ContentAlignment.MiddleLeft);
    end);

    if (Colors ~= nil) then
        local role = options.color or "text";
        label:SetForeColor(Colors.color[role] or Colors.color.text);
        -- A dark outline keeps text readable over bright scenery.
        pcall(function()
            label:SetOutlineColor(Colors.Alpha("shadow", 0.85));
            label:SetFontStyle(Turbine.UI.FontStyle.Outline);
        end);
    end

    if (options.text ~= nil) then
        label:SetText(options.text);
    end
    return label;
end

MithrilUI.Core.Window = Window;
