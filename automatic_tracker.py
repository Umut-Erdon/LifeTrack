"""Privacy-conscious Windows foreground-app usage tracking helpers.

Only executable names are collected. Window titles, typed text, URLs and screenshots
are never read or stored. Tracking starts only after the user presses Start.
"""
from __future__ import annotations

import os
from pathlib import Path

# Executable names are normalized without the .exe suffix. Keep categories aligned
# with database.VALID_CATEGORIES so every automatic record passes validation.
CATEGORY_RULES = {
    "Sosyal medya": {
        "instagram", "tiktok", "facebook", "snapchat", "x", "threads",
        "pinterest", "reddit", "telegramwebview",
    },
    "Video / içerik": {
        "spotify", "vlc", "netflix", "youtube", "disneyplus", "mpc-hc",
        "mpc-hc64", "potplayer", "wmplayer", "obs64", "twitch",
    },
    "Oyun": {
        "steam", "steamwebhelper", "epicgameslauncher", "valorant",
        "leagueclient", "league of legends", "cs2", "dota2", "minecraft",
        "robloxplayerbeta", "battle.net", "riotclientservices", "eadesktop",
        "xboxpcapp", "playnite",
    },
    "İş / eğitim": {
        "code", "devenv", "pycharm64", "python", "pythonw", "excel",
        "winword", "powerpnt", "notion", "obsidian", "onenote", "sublime_text",
        "cursor", "windsurf", "rider64", "idea64", "webstorm64", "phpstorm64",
        "ssms", "azuredatastudio", "xampp-control", "docker desktop",
        "windows terminal", "windowsterminal", "notepad", "notepad++",
        "acrobat", "foxitreader", "libreoffice", "zoom workplace",
    },
    "İletişim": {
        "discord", "teams", "ms-teams", "zoom", "skype", "telegram",
        "whatsapp", "slack", "signal", "outlook", "thunderbird", "webex",
    },
}

BROWSER_NAMES = {
    "chrome", "msedge", "firefox", "opera", "brave", "vivaldi",
    "iexplore", "arc", "browser",
}

DISPLAY_NAMES = {
    "msedge": "Microsoft Edge", "chrome": "Google Chrome",
    "code": "Visual Studio Code", "devenv": "Visual Studio",
    "ms-teams": "Microsoft Teams", "winword": "Microsoft Word",
    "powerpnt": "Microsoft PowerPoint", "ssms": "SQL Server Management Studio",
    "steamwebhelper": "Steam", "riotclientservices": "Riot Client",
}

def classify_process(executable: str) -> tuple[str, str]:
    """Return (display app name, category) from executable name only."""
    stem = Path(str(executable or "")).stem.lower().strip()
    if not stem:
        return "Bilinmeyen uygulama", "Diğer"
    display = DISPLAY_NAMES.get(stem, stem[:1].upper() + stem[1:])
    for category, names in CATEGORY_RULES.items():
        if stem in names:
            return display, category
    if stem in BROWSER_NAMES:
        return f"{display} (tarayıcı)", "Diğer"
    return display, "Diğer"

def get_foreground_executable() -> str | None:
    """Get foreground executable on Windows, returning None when idle/errors.

    More than 60 seconds without keyboard/mouse input is treated as idle. The
    function does not read a window title, page URL, typed text or screen content.
    """
    if os.name != "nt":
        return None
    try:
        import ctypes
        from ctypes import wintypes
        import psutil

        user32 = ctypes.windll.user32
        kernel32 = ctypes.windll.kernel32

        class LASTINPUTINFO(ctypes.Structure):
            _fields_ = [("cbSize", wintypes.UINT), ("dwTime", wintypes.DWORD)]

        info = LASTINPUTINFO()
        info.cbSize = ctypes.sizeof(LASTINPUTINFO)
        if not user32.GetLastInputInfo(ctypes.byref(info)):
            return None
        tick = kernel32.GetTickCount()
        idle_ms = (int(tick) - int(info.dwTime)) & 0xFFFFFFFF
        if idle_ms > 60_000:
            return None

        hwnd = user32.GetForegroundWindow()
        if not hwnd:
            return None
        pid = wintypes.DWORD()
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        if not pid.value or pid.value == os.getpid():
            return None
        return psutil.Process(pid.value).name()
    except Exception:
        # Tracking must never crash the UI because a process exits mid-sample.
        return None
