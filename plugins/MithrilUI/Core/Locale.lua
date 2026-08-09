--[[
    MithrilUI.Core.Locale -- German and English strings.

    Falls back to English for anything missing, and to the key itself if a
    string was never defined, so a missing translation shows up as an obvious
    identifier rather than an empty label.
]]

import "Turbine";

MithrilUI = MithrilUI or {};
MithrilUI.Core = MithrilUI.Core or {};

local Locale = {};

local strings = {};

strings.en = {
    ["ui.lock"]            = "Lock";
    ["ui.unlock"]          = "Unlock";
    ["ui.locked"]          = "Windows locked";
    ["ui.unlocked"]        = "Windows unlocked, drag them where you want";
    ["ui.reset"]           = "Window positions reset";
    ["ui.close"]           = "Close";

    ["data.coords"]        = "Coords";
    ["data.bags"]          = "Bags";
    ["data.morale"]        = "Morale";
    ["data.power"]         = "Power";
    ["data.level"]         = "Level";
    ["data.session"]       = "Session";
    ["data.unavailable"]   = "n/a";

    ["buffs.buffs"]        = "Buffs";
    ["buffs.debuffs"]      = "Debuffs";
    ["buffs.none"]         = "no effects";

    ["cmd.help"]           = "Commands:";
    ["cmd.help.config"]    = "/mithril config    open the control panel";
    ["cmd.help.lock"]      = "/mithril lock      lock or unlock all windows";
    ["cmd.help.reset"]     = "/mithril reset     move every window back to its default spot";
    ["cmd.help.diag"]      = "/mithril diag      report which game APIs this client exposes";
    ["cmd.unknown"]        = "Unknown command. Try /mithril help";

    ["diag.title"]         = "API capability report";
    ["diag.summary"]       = "%d available, %d unavailable";
    ["diag.hint"]          = "Unavailable entries simply disable a feature. Nothing is broken.";

    ["suite.title"]        = "MithrilUI";
    ["suite.modules"]      = "Modules";
    ["suite.loaded"]       = "loaded";
    ["suite.notloaded"]    = "not loaded";
    ["suite.hint"]         = "Load modules from the in-game Plugin Manager.";
};

strings.de = {
    ["ui.lock"]            = "Sperren";
    ["ui.unlock"]          = "Entsperren";
    ["ui.locked"]          = "Fenster gesperrt";
    ["ui.unlocked"]        = "Fenster entsperrt, jetzt frei verschiebbar";
    ["ui.reset"]           = "Fensterpositionen zurückgesetzt";
    ["ui.close"]           = "Schließen";

    ["data.coords"]        = "Koord.";
    ["data.bags"]          = "Taschen";
    ["data.morale"]        = "Moral";
    ["data.power"]         = "Kraft";
    ["data.level"]         = "Stufe";
    ["data.session"]       = "Sitzung";
    ["data.unavailable"]   = "k.A.";

    ["buffs.buffs"]        = "Stärkungen";
    ["buffs.debuffs"]      = "Schwächungen";
    ["buffs.none"]         = "keine Effekte";

    ["cmd.help"]           = "Befehle:";
    ["cmd.help.config"]    = "/mithril config    Steuerfenster öffnen";
    ["cmd.help.lock"]      = "/mithril lock      alle Fenster sperren oder entsperren";
    ["cmd.help.reset"]     = "/mithril reset     alle Fenster auf Standardposition";
    ["cmd.help.diag"]      = "/mithril diag      zeigt, welche Spiel-APIs dieser Client bietet";
    ["cmd.unknown"]        = "Unbekannter Befehl. Versuch /mithril help";

    ["diag.title"]         = "API-Fähigkeitsbericht";
    ["diag.summary"]       = "%d verfügbar, %d nicht verfügbar";
    ["diag.hint"]          = "Nicht verfügbare Einträge schalten nur eine Funktion ab. Nichts ist kaputt.";

    ["suite.title"]        = "MithrilUI";
    ["suite.modules"]      = "Module";
    ["suite.loaded"]       = "geladen";
    ["suite.notloaded"]    = "nicht geladen";
    ["suite.hint"]         = "Module über den Plugin-Manager im Spiel laden.";
};

local active = "en";

local function detect()
    local ok, locale = pcall(function() return Turbine.Engine.GetLocale(); end);
    if (ok and type(locale) == "string") then
        local lowered = string.lower(locale);
        if (string.find(lowered, "de") ~= nil) then
            return "de";
        end
    end
    return "en";
end

active = detect();

function Locale.SetLanguage(code)
    if (strings[code] ~= nil) then
        active = code;
        return true;
    end
    return false;
end

function Locale.GetLanguage()
    return active;
end

--[[ Look up a key, optionally with string.format arguments. ]]
function Locale.Get(key, ...)
    local table_for_locale = strings[active] or strings.en;
    local value = table_for_locale[key] or strings.en[key] or key;
    if (select("#", ...) > 0) then
        local ok, formatted = pcall(string.format, value, ...);
        if (ok) then return formatted; end
    end
    return value;
end

MithrilUI.Core.Locale = Locale;
