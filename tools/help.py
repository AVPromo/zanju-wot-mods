"""Show repo-tool environment guidance and the available custom commands."""

from __future__ import annotations

import os
import shutil
import sys

from .console import section, success, warning
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
        "usage": "wot_mods_build (--all | [mod ...])",
        "module": "python -m tools.build research-progress-bar",
        "description": "Build .wotmod packages and release bundles.",
    },
    {
        "name": "wot_mods_cleanup",
        "usage": "wot_mods_cleanup (--all | [mod ...])",
        "module": "python -m tools.cleanup research-progress-bar",
        "description": "Remove deployed WoT packages and config for the selected mods.",
    },
    {
        "name": "wot_mods_cycle",
        "usage": "wot_mods_cycle (--all | [mod ...])",
        "module": "python -m tools.cycle research-progress-bar",
        "description": "Run cleanup + build + deploy in one command.",
    },
    {
        "name": "wot_mods_deploy",
        "usage": "wot_mods_deploy (--all | [mod ...])",
        "module": "python -m tools.deploy research-progress-bar",
        "description": "Copy pre-built packages and config into the configured WoT install. Run wot_mods_build first.",
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
        "name": "wot_mods_update_wot_version_manifest",
        "usage": "wot_mods_update_wot_version_manifest",
        "module": "python -m tools.update_wot_version_manifest",
        "description": "Refresh the pinned WoT client version manifest from version.xml or explicit version input.",
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
    section("Environment")
    success("Repo root: {}".format(REPO_ROOT))
    success("Current Python: {}".format(sys.executable))
    if _is_venv_active():
        success("Active venv: yes")
    else:
        warning("Active venv: no")
    if os.path.isfile(ENV_PATH):
        success(".env file: found")
    else:
        warning(".env file: missing")

    section("PowerShell setup")
    success(r".\.venv\Scripts\Activate.ps1")
    success("python -m pip install -e .")
    success(r".\.venv\Scripts\python.exe -m tools.help")
    warning("If a new wot_mods_* command does not resolve after pulling repo changes,")
    warning("rerun python -m pip install -e . inside the repo venv to regenerate")
    warning("the console-script stubs.")


def _print_commands_section():
    section("Available custom commands")
    for command in COMMANDS:
        status, detail = _command_resolution(command["name"])
        if status == "available":
            success("{} [available]".format(command["usage"]))
        else:
            warning("{} [missing]".format(command["usage"]))
        print("  {}".format(command["description"]))
        print("  Module fallback: {}".format(command["module"]))
        print("  Resolved: {}".format(detail))
        print()


def main():
    section("Zanju WoT Mods Tool Help")
    _print_environment_section()
    _print_commands_section()


if __name__ == "__main__":
    main()
