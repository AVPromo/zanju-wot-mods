"""Refresh the tracked WoT client version manifest (the single source of the version pin)."""

from __future__ import annotations

import argparse

from .console import detail, section, success
from .paths import ENV_PATH
from .wot_version import (
    WotVersionError,
    load_wot_version_manifest,
    parse_version_xml,
    save_wot_version_manifest,
)


def load_env(path):
    env = {}
    try:
        with open(path, "r", encoding="utf-8") as fh:
            for raw in fh:
                line = raw.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, value = line.split("=", 1)
                env[key.strip()] = value.strip().strip('"').strip("'")
    except OSError:
        return env
    return env


def parse_args(argv):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--wot-game-dir",
        help="Override the WoT game directory used to read version.xml.",
    )
    parser.add_argument(
        "--version",
        help="Set a specific WoT client version (X.Y.Z.W) without reading version.xml.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would change without writing the manifest.",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Print additional diagnostic details.",
    )
    return parser.parse_args(argv)


def _resolve_target_version(args):
    if args.version and args.wot_game_dir:
        raise WotVersionError("Use either --version or --wot-game-dir, not both")

    if args.version:
        return args.version.strip(), "cli"

    game_dir = "{}".format(args.wot_game_dir or "").strip()
    if not game_dir:
        game_dir = load_env(ENV_PATH).get("WOT_GAME_DIR", "").strip()
    if not game_dir:
        raise WotVersionError("Set WOT_GAME_DIR in .env or pass --wot-game-dir")

    return parse_version_xml(game_dir), game_dir


def _main(argv=None):
    args = parse_args(argv)
    section("Update WoT version manifest")

    current_version = load_wot_version_manifest()["wotClientVersion"]
    target_version, source = _resolve_target_version(args)
    manifest_needs_update = target_version != current_version

    if not manifest_needs_update:
        success("No version changes detected")
        detail("Pinned version: {}".format(current_version), verbose=args.verbose)
        return

    if args.dry_run:
        success("Dry-run: manifest would change {} -> {}".format(current_version, target_version))
        detail("Source: {}".format(source), verbose=args.verbose)
        return

    save_wot_version_manifest(target_version)
    success("WoT version manifest updated: {} -> {}".format(current_version, target_version))
    detail("Source: {}".format(source), verbose=args.verbose)


def main(argv=None):
    try:
        return _main(argv)
    except WotVersionError as exc:
        raise SystemExit(str(exc)) from None


if __name__ == "__main__":
    main()
