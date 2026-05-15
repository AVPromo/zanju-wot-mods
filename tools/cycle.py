"""
Development/test quick cycle helper for WoT mods.

Runs cleanup + deploy in one command.

Usage:
    wot_mods_cycle
    wot_mods_cycle research-progress-bar
    wot_mods_cycle --dry-run
    wot_mods_cycle --fresh-log
    python -m tools.cycle research-progress-bar

Behavior:
- Without args: cycles all mods under mods/
- With mod args: cycles only selected mods
- With --dry-run: runs cleanup in dry-run mode and skips deploy
- With --fresh-log: truncates python.log before cycle (no archive, opt-in)
- The cycle updates files on disk only; WoT must be restarted to load changed
    Python/UI/package assets.
"""

from __future__ import annotations

import os
import subprocess
import sys

from .paths import ENV_PATH


def load_env(path):
    env = {}
    if not os.path.isfile(path):
        return env

    with open(path, "r", encoding="utf-8") as fh:
        for raw in fh:
            line = raw.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            env[key.strip()] = value.strip().strip('"').strip("'")
    return env


def is_wot_running():
    try:
        result = subprocess.run(
            ["tasklist"],
            check=False,
            capture_output=True,
            text=True,
        )
        output = (result.stdout or "").lower()
        # Common WoT executable names seen across installs/launchers.
        names = [
            "worldoftanks",
            "worldoftanks64",
            "worldoftanks.exe",
            "worldoftanks64.exe",
        ]
        return any(name in output for name in names)
    except Exception:
        return False


def fresh_log(dry_run):
    env = load_env(ENV_PATH)
    game_dir = env.get("WOT_GAME_DIR", "")
    if not game_dir:
        raise RuntimeError("WOT_GAME_DIR is not set in .env (required for --fresh-log).")

    log_path = os.path.join(game_dir, "python.log")

    if is_wot_running():
        raise RuntimeError("WoT process appears to be running; close the game before using --fresh-log.")

    if dry_run:
        print("DRY-RUN fresh-log: would truncate {}".format(log_path))
        return

    os.makedirs(game_dir, exist_ok=True)
    with open(log_path, "w", encoding="utf-8"):
        pass
    print("Fresh log created: {}".format(log_path))


def run_cmd(cmd):
    print("Running:", " ".join(cmd))
    subprocess.check_call(cmd)


def parse_args(argv):
    dry_run = False
    fresh_log_flag = False
    mod_names = []
    for arg in argv:
        if arg == "--dry-run":
            dry_run = True
        elif arg == "--fresh-log":
            fresh_log_flag = True
        else:
            mod_names.append(arg)
    return dry_run, fresh_log_flag, mod_names


def main():
    dry_run, fresh_log_flag, mod_names = parse_args(sys.argv[1:])
    wot_running_before_cycle = is_wot_running()

    if wot_running_before_cycle:
        print(
            "WARNING: WoT appears to be running. The cycle can update files on disk,"
            " but the current client session will not hot-reload Python/UI/package changes."
        )

    if fresh_log_flag:
        fresh_log(dry_run)

    cleanup_cmd = [sys.executable, "-m", "tools.cleanup"]
    if dry_run:
        cleanup_cmd.append("--dry-run")
    cleanup_cmd.extend(mod_names)

    run_cmd(cleanup_cmd)

    if dry_run:
        print("Dry-run mode: deploy step skipped.")
        return

    deploy_cmd = [sys.executable, "-m", "tools.deploy"]
    deploy_cmd.extend(mod_names)
    run_cmd(deploy_cmd)

    print("Done. Cleanup + deploy cycle completed.")
    if wot_running_before_cycle:
        print("Next step: restart WoT to load the updated mod package.")
    else:
        print("Next step: launch WoT to load the updated mod package.")


if __name__ == "__main__":
    main()
