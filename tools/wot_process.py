from __future__ import annotations

import subprocess

_WOT_PROCESS_NAMES = (
    "worldoftanks",
    "worldoftanks64",
    "worldoftanks.exe",
    "worldoftanks64.exe",
)


def is_wot_running():
    try:
        result = subprocess.run(
            ["tasklist"],
            check=False,
            capture_output=True,
            text=True,
        )
        output = (result.stdout or "").lower()
        return any(name in output for name in _WOT_PROCESS_NAMES)
    except Exception:
        return False


def ensure_wot_not_running(command_name):
    if is_wot_running():
        raise RuntimeError("WoT appears to be running. Close the game before using {}.".format(command_name))
