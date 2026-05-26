"""
Development/test quick cycle helper for WoT mods.

Runs cleanup + build + deploy in one command.

Usage:
    wot_mods_cycle --all
    wot_mods_cycle research-progress-bar
    wot_mods_cycle mod-a mod-b
    wot_mods_cycle --dry-run
    wot_mods_cycle --fresh-log
    wot_mods_cycle --verbose research-progress-bar
    python -m tools.cycle research-progress-bar

Behavior:
- With --all: cycles all mods under mods/
- With mod args: cycles only selected mods
- With --dry-run: runs cleanup in dry-run mode and skips build + deploy
- With --fresh-log: truncates python.log before cycle (no archive, opt-in)
- The cycle requires WoT to be closed; it exits before cleanup if the client is running
- The cycle updates files on disk only; WoT must be restarted to load changed
    Python/UI/package assets.
"""

from __future__ import annotations

import os
import subprocess
import sys

from .console import detail, section, success, warning
from .paths import ENV_PATH, MODS_DIR
from .wot_process import ensure_wot_not_running, is_wot_running


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


def fresh_log(dry_run):
    env = load_env(ENV_PATH)
    game_dir = env.get("WOT_GAME_DIR", "")
    if not game_dir:
        raise RuntimeError("WOT_GAME_DIR is not set in .env (required for --fresh-log).")

    log_path = os.path.join(game_dir, "python.log")

    if is_wot_running():
        raise RuntimeError("WoT process appears to be running; close the game before using --fresh-log.")

    if dry_run:
        success("Dry-run: fresh log would be created")
        detail("Path: {}".format(log_path), verbose=True)
        return

    os.makedirs(game_dir, exist_ok=True)
    with open(log_path, "w", encoding="utf-8"):
        pass
    success("Fresh log created")
    detail("Path: {}".format(log_path), verbose=True)


def run_cmd(cmd, verbose=False):
    detail("Running: {}".format(" ".join(cmd)), verbose=verbose)
    subprocess.check_call(cmd)


def discover_mods():
    if not os.path.isdir(MODS_DIR):
        return []
    return sorted(d for d in os.listdir(MODS_DIR) if os.path.isdir(os.path.join(MODS_DIR, d)))


def parse_args(argv):
    dry_run = False
    run_all = False
    fresh_log_flag = False
    verbose = False
    mod_names = []
    for arg in argv:
        if arg == "--dry-run":
            dry_run = True
        elif arg == "--all":
            run_all = True
        elif arg == "--fresh-log":
            fresh_log_flag = True
        elif arg == "--verbose":
            verbose = True
        else:
            mod_names.append(arg)
    return dry_run, run_all, fresh_log_flag, verbose, mod_names


def _print_targeting_help(available_mods):
    warning("No mod targets provided")
    success("Use --all to cycle all mods, or pass one or more mod names")
    if available_mods:
        success("Available mods: {}".format(", ".join(available_mods)))
    else:
        warning("No mods found under mods/")


def _main():
    dry_run, run_all, fresh_log_flag, verbose, requested_mods = parse_args(sys.argv[1:])
    if run_all and requested_mods:
        raise RuntimeError("Use either --all or explicit mod names, not both")

    available_mods = discover_mods()
    if run_all:
        mod_names = available_mods
    elif requested_mods:
        mod_names = requested_mods
    else:
        _print_targeting_help(available_mods)
        return

    if not mod_names:
        warning("No mods found under mods/")
        return

    ensure_wot_not_running("wot_mods_cycle")

    if fresh_log_flag:
        fresh_log(dry_run)

    cleanup_cmd = [sys.executable, "-m", "tools.cleanup"]
    if run_all:
        cleanup_cmd.append("--all")
    if dry_run:
        cleanup_cmd.append("--dry-run")
    if verbose:
        cleanup_cmd.append("--verbose")
    if not run_all:
        cleanup_cmd.extend(mod_names)

    section("Step 1/3: cleanup")
    run_cmd(cleanup_cmd, verbose=verbose)

    if dry_run:
        success("Dry-run mode: build + deploy steps skipped.")
        return

    build_cmd = [sys.executable, "-m", "tools.build"]
    if run_all:
        build_cmd.append("--all")
    if verbose:
        build_cmd.append("--verbose")
    if not run_all:
        build_cmd.extend(mod_names)
    section("Step 2/3: build")
    run_cmd(build_cmd, verbose=verbose)

    deploy_cmd = [sys.executable, "-m", "tools.deploy"]
    if run_all:
        deploy_cmd.append("--all")
    if verbose:
        deploy_cmd.append("--verbose")
    if not run_all:
        deploy_cmd.extend(mod_names)
    section("Step 3/3: deploy")
    run_cmd(deploy_cmd, verbose=verbose)

    section("Cycle complete")
    success("Cleanup + build + deploy finished.")
    success("Next step: launch WoT to load the updated mod package.")


def main():
    try:
        return _main()
    except RuntimeError as exc:
        raise SystemExit(str(exc)) from None


if __name__ == "__main__":
    main()
