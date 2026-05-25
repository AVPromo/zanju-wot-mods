"""Show repo-tool environment guidance and the available custom commands."""

from __future__ import annotations

import os
import shutil
import sys

from .paths import ENV_PATH, REPO_ROOT

COMMANDS = [
    {
        "name": "wot_mods_help",
        "usage": "wot_mods_help",
        "module": "python -m tools.help",
        "description": "Show repo environment guidance and the available custom commands.",
    },
    {
        "name": "wot_mods_build",
        "usage": "wot_mods_build [mod ...]",
        "module": "python -m tools.build research-progress-bar",
        "description": "Build .wotmod packages and release bundles.",
    },
    {
        "name": "wot_mods_cleanup",
        "usage": "wot_mods_cleanup [mod ...]",
        "module": "python -m tools.cleanup research-progress-bar",
        "description": "Remove built artifacts from dist/ and deployed WoT targets.",
    },
    {
        "name": "wot_mods_cycle",
        "usage": "wot_mods_cycle [mod ...]",
        "module": "python -m tools.cycle research-progress-bar",
        "description": "Run cleanup plus deploy in one command.",
    },
    {
        "name": "wot_mods_deploy",
        "usage": "wot_mods_deploy [mod ...]",
        "module": "python -m tools.deploy research-progress-bar",
        "description": "Build and copy packages plus config into the configured WoT install.",
    },
    {
        "name": "wot_mods_fetch_companion_artifacts",
        "usage": "wot_mods_fetch_companion_artifacts",
        "module": "python -m tools.fetch_companion_artifacts",
        "description": "Populate the ignored local cache with manifest-pinned companion .wotmod files.",
    },
    {
        "name": "wot_mods_update_companion_manifest",
        "usage": "wot_mods_update_companion_manifest",
        "module": "python -m tools.update_companion_manifest",
        "description": "Refresh the tracked companion-artifact manifest from upstream release metadata.",
    },
    {
        "name": "wot_mods_lint",
        "usage": "wot_mods_lint [subcommand]",
        "module": "python -m tools.lint check",
        "description": "Run the repo Python format and lint workflow.",
    },
]


def _is_venv_active():
    return sys.prefix != getattr(sys, "base_prefix", sys.prefix)


def _command_resolution(name):
    resolved = shutil.which(name)
    if resolved:
        return "available", resolved
    return "missing", "not found on PATH"


def _print_environment_section():
    print("Environment")
    print("-----------")
    print("Repo root: {}".format(REPO_ROOT))
    print("Current Python: {}".format(sys.executable))
    print("Active venv: {}".format("yes" if _is_venv_active() else "no"))
    print(".env file: {}".format("found" if os.path.isfile(ENV_PATH) else "missing"))
    print()
    print("PowerShell setup")
    print("----------------")
    print(r".\.venv\Scripts\Activate.ps1")
    print("python -m pip install -e .")
    print(r".\.venv\Scripts\python.exe -m tools.help")
    print()
    print("If a new wot_mods_* command does not resolve after pulling repo changes,")
    print("rerun `python -m pip install -e .` inside the repo venv to regenerate")
    print("the console-script stubs.")


def _print_commands_section():
    print("Available custom commands")
    print("-------------------------")
    for command in COMMANDS:
        status, detail = _command_resolution(command["name"])
        print("{} [{}]".format(command["usage"], status))
        print("  {}".format(command["description"]))
        print("  module fallback: {}".format(command["module"]))
        print("  resolved: {}".format(detail))
        print()


def main():
    print("Zanju WoT Mods Tool Help")
    print("========================")
    print()
    _print_environment_section()
    print()
    _print_commands_section()


if __name__ == "__main__":
    main()
