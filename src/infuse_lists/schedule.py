"""Install/remove the launchd agent that runs `infuse-lists apply --scheduled` periodically."""
import os
import plistlib
import subprocess
import sys

from . import paths

LABEL = "io.github.lbnsq182.infuse-lists"
AGENT = os.path.expanduser(f"~/Library/LaunchAgents/{LABEL}.plist")
DAYS = ["sunday", "monday", "tuesday", "wednesday", "thursday", "friday", "saturday"]


def python_binary():
    """The interpreter that must be granted Full Disk Access."""
    return os.path.realpath(sys.executable)


def install(day="sunday", hour=4, minute=0, every_day=False):
    interval = {"Hour": hour, "Minute": minute}
    if not every_day:
        interval["Weekday"] = DAYS.index(day.lower())
    agent = {
        "Label": LABEL,
        "ProgramArguments": [python_binary(), "-m", "infuse_lists", "apply", "--scheduled"],
        "StartCalendarInterval": interval,
        "StandardOutPath": paths.LOG,
        "StandardErrorPath": paths.LOG,
        # pipx venv site-packages must stay importable when called with the base interpreter
        "EnvironmentVariables": {"PYTHONPATH": os.pathsep.join(p for p in sys.path if p.endswith("site-packages"))},
    }
    os.makedirs(os.path.dirname(AGENT), exist_ok=True)
    os.makedirs(os.path.dirname(paths.LOG), exist_ok=True)
    uninstall(quiet=True)
    with open(AGENT, "wb") as f:
        plistlib.dump(agent, f)
    subprocess.run(["launchctl", "bootstrap", f"gui/{os.getuid()}", AGENT], check=True)


def uninstall(quiet=False):
    subprocess.run(["launchctl", "bootout", f"gui/{os.getuid()}/{LABEL}"], capture_output=True)
    if os.path.exists(AGENT):
        os.remove(AGENT)
    elif not quiet:
        print("No schedule installed.")


def run_now():
    subprocess.run(["launchctl", "kickstart", f"gui/{os.getuid()}/{LABEL}"], check=True)


def installed():
    return os.path.exists(AGENT)
