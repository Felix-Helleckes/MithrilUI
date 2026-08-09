--[[
    MithrilUI Suite -- the /mithril command and the control panel.

    Load this one first. It owns the shared state that the display modules
    read: the window lock, saved positions, and the API capability report.
    The display modules work without it, they just lose the chat command.
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

local MODULE = "Suite";

local defaults = {
    locked = true,
};

local settings = Settings.For(MODULE, defaults);
local panel = nil;
local command = nil;

-- -- control panel ---------------------------------------------------------

local MODULES = { "Databar", "Vitals", "BuffBars" };

local function closePanel()
    if (panel ~= nil) then
        if (panel.MithrilDispose ~= nil) then panel.MithrilDispose(); end
        panel = nil;
    end
end

local function openPanel()
    if (panel ~= nil) then
        closePanel();
        return;
    end

    local width, lineHeight = 260, 18;
    panel = UIWindow.New({
        module = MODULE,
        width = width,
        height = 60 + #MODULES * lineHeight,
        x = 200,
        y = 200,
        background = "panelAlt",
    });

    local y = 6;
    UIWindow.Label(panel, 8, y, width - 16, lineHeight,
        { text = L.Get("suite.title") .. "  " .. Util.VERSION, color = "accent" });
    y = y + lineHeight + 4;

    UIWindow.Label(panel, 8, y, width - 16, lineHeight,
        { text = L.Get("suite.modules"), color = "textDim" });
    y = y + lineHeight;

    for _, name in ipairs(MODULES) do
        local module = MithrilUI[name];
        local loaded = (module ~= nil and module.IsLoaded ~= nil and module.IsLoaded());
        UIWindow.Label(panel, 16, y, width - 32, lineHeight, {
            text = name .. "  -  "
                .. L.Get(loaded and "suite.loaded" or "suite.notloaded"),
            color = loaded and "good" or "textDim",
        });
        y = y + lineHeight;
    end

    y = y + 4;
    UIWindow.Label(panel, 8, y, width - 16, lineHeight,
        { text = L.Get("suite.hint"), color = "textDim" });
end

-- -- commands --------------------------------------------------------------

local function showHelp()
    Util.PrintRaw(L.Get("cmd.help"));
    Util.PrintRaw("  " .. L.Get("cmd.help.config"));
    Util.PrintRaw("  " .. L.Get("cmd.help.lock"));
    Util.PrintRaw("  " .. L.Get("cmd.help.reset"));
    Util.PrintRaw("  " .. L.Get("cmd.help.diag"));
end

--[[ The capability report. This is the first thing to ask someone for when a
     module "does nothing" on their client. ]]
local function showDiagnostics()
    -- Touch every probe so the report covers what was never called yet.
    Api.GetName(); Api.GetLevel(); Api.GetClassName();
    Api.GetMorale(); Api.GetPower();
    Api.GetPosition(); Api.GetBagSpace(); Api.GetEffects();
    Api.GetScreenSize();

    local lines, available, missing = Api.Report();
    Util.PrintRaw("--- MithrilUI " .. L.Get("diag.title") .. " ---");
    for _, line in ipairs(lines) do
        Util.PrintRaw(line);
    end
    Util.PrintRaw(L.Get("diag.summary", available, missing));
    Util.PrintRaw(L.Get("diag.hint"));
end

local function toggleLock()
    local isLocked = UIWindow.ToggleLock();
    settings.locked = isLocked;
    Settings.MarkDirty();
    Settings.Save(true);
    Util.Print(L.Get(isLocked and "ui.locked" or "ui.unlocked"));
end

local function execute(_, _, arguments)
    local parts = Util.Split(Util.Trim(arguments or ""), " ");
    local verb = string.lower(parts[1] or "");

    if (verb == "" or verb == "help" or verb == "?") then
        showHelp();
    elseif (verb == "config" or verb == "options" or verb == "panel") then
        openPanel();
    elseif (verb == "lock" or verb == "unlock") then
        toggleLock();
    elseif (verb == "reset") then
        UIWindow.ResetPositions();
        Util.Print(L.Get("ui.reset"));
    elseif (verb == "diag" or verb == "diagnostics") then
        showDiagnostics();
    else
        Util.Print(L.Get("cmd.unknown"));
    end
end

-- -- lifecycle -------------------------------------------------------------

local function start()
    UIWindow.SetLocked(settings.locked ~= false);

    command = Turbine.ShellCommand();
    command.Execute = execute;
    command.GetHelp = function()
        return "MithrilUI: /mithril help";
    end

    local ok = pcall(function()
        Turbine.Shell.AddCommand("mithril;mui", command);
    end);
    if (not ok) then
        Util.Print("could not register the /mithril command");
    end

    Util.Print("v" .. Util.VERSION .. " ready. /mithril help");
end

local function stop()
    closePanel();
    if (command ~= nil) then
        pcall(function() Turbine.Shell.RemoveCommand(command); end);
        command = nil;
    end
    Settings.Save(true);
end

MithrilUI.Suite = {
    OpenPanel = openPanel,
    IsLoaded = function() return command ~= nil; end,
};

start();

Plugins["MithrilUI"].Unload = function()
    stop();
end
