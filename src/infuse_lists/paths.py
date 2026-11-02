"""Locations of Infuse's data on macOS and helpers to control the app."""
import os
import plistlib
import subprocess
import time

CONTAINER = os.path.expanduser("~/Library/Containers/com.firecore.infuse/Data")
PREFS = os.path.join(CONTAINER, "Library/Preferences/InternalPrefs")
META_DB = os.path.join(PREFS, "com.firecore.media.meta.db")
PLAYLISTS = os.path.join(PREFS, "com.firecore.infuse.Playlists.plist")
VFS = os.path.join(PREFS, "com.firecore.media.VFS.plist")
APP = "/Applications/Infuse.app"

CONFIG = os.path.expanduser("~/.config/infuse-lists/config.toml")
SUPPORT = os.path.expanduser("~/Library/Application Support/infuse-lists")
STATE = os.path.join(SUPPORT, "state.json")
BACKUPS = os.path.join(SUPPORT, "backups")
CACHE = os.path.expanduser("~/Library/Caches/infuse-lists")
LOG = os.path.expanduser("~/Library/Logs/infuse-lists.log")

# Versions whose file formats were verified; others are preview-only unless --force
TESTED_VERSIONS = ("8.5",)


def infuse_version():
    try:
        with open(os.path.join(APP, "Contents/Info.plist"), "rb") as f:
            return plistlib.load(f).get("CFBundleShortVersionString")
    except OSError:
        return None


def version_supported(version):
    return bool(version) and any(version == v or version.startswith(v + ".") for v in TESTED_VERSIONS)


def infuse_running():
    return subprocess.run(["pgrep", "-xq", "Infuse"]).returncode == 0


def quit_infuse(timeout=60):
    subprocess.run(["osascript", "-e", 'tell application "Infuse" to quit'], capture_output=True)
    for _ in range(timeout):
        if not infuse_running():
            return True
        time.sleep(1)
    return False


def open_infuse():
    subprocess.run(["open", "-g", "-a", "Infuse"])
