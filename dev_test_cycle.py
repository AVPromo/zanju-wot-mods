"""
Development/test quick cycle helper for WoT mods.

Runs cleanup + deploy in one command.

Usage:
    python dev_test_cycle.py
    python dev_test_cycle.py research-progress-bar
    python dev_test_cycle.py --dry-run

Behavior:
- Without args: cycles all mods under mods/
- With mod args: cycles only selected mods
- With --dry-run: runs cleanup in dry-run mode and skips deploy
"""

from __future__ import annotations

import os
import subprocess
import sys

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))


def run_cmd(cmd):
    print('Running:', ' '.join(cmd))
    subprocess.check_call(cmd)


def parse_args(argv):
    dry_run = False
    mod_names = []
    for arg in argv:
        if arg == '--dry-run':
            dry_run = True
        else:
            mod_names.append(arg)
    return dry_run, mod_names


def main():
    dry_run, mod_names = parse_args(sys.argv[1:])

    cleanup_cmd = [sys.executable, os.path.join(SCRIPT_DIR, 'dev_test_cleanup.py')]
    if dry_run:
        cleanup_cmd.append('--dry-run')
    cleanup_cmd.extend(mod_names)

    run_cmd(cleanup_cmd)

    if dry_run:
        print('Dry-run mode: deploy step skipped.')
        return

    deploy_cmd = [sys.executable, os.path.join(SCRIPT_DIR, 'dev_test_deploy.py')]
    deploy_cmd.extend(mod_names)
    run_cmd(deploy_cmd)

    print('Done. Cleanup + deploy cycle completed.')


if __name__ == '__main__':
    main()
