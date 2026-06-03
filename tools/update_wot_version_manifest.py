"""Refresh the tracked WoT client version manifest and sync authored mod meta.xml files."""

from __future__ import annotations

import argparse
import os
import xml.etree.ElementTree as ET

from .console import detail, section, success
from .paths import ENV_PATH, MODS_DIR
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
        help="Show what would change without writing the manifest or mod metadata files.",
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


def _iter_mod_meta_paths():
    if not os.path.isdir(MODS_DIR):
        return []

    meta_paths = []
    for mod_name in sorted(os.listdir(MODS_DIR)):
        meta_path = os.path.join(MODS_DIR, mod_name, "meta.xml")
        if os.path.isfile(meta_path):
            meta_paths.append(meta_path)
    return meta_paths


def _find_meta_updates(target_version):
    updates = []
    for meta_path in _iter_mod_meta_paths():
        root = ET.parse(meta_path).getroot()
        current_version = (root.findtext("wot_client_version", "") or "").strip()
        if current_version == target_version:
            continue
        updates.append(
            {
                "path": meta_path,
                "current_version": current_version,
            }
        )
    return updates


def _write_meta_updates(meta_updates, target_version):
    for item in meta_updates:
        meta_path = item["path"]
        tree = ET.parse(meta_path)
        root = tree.getroot()
        version_node = root.find("wot_client_version")
        if version_node is None:
            version_node = ET.SubElement(root, "wot_client_version")
        version_node.text = target_version
        ET.indent(tree, space="    ")
        tree.write(meta_path, encoding="utf-8", xml_declaration=True)


def _main(argv=None):
    args = parse_args(argv)
    section("Update WoT version manifest")

    current_version = load_wot_version_manifest()["wotClientVersion"]
    target_version, source = _resolve_target_version(args)
    manifest_needs_update = target_version != current_version
    meta_updates = _find_meta_updates(target_version)

    if not manifest_needs_update and not meta_updates:
        success("No version changes detected")
        detail("Pinned version: {}".format(current_version), verbose=args.verbose)
        return

    if args.dry_run:
        if manifest_needs_update:
            success("Dry-run: manifest would change {} -> {}".format(current_version, target_version))
        else:
            success("Dry-run: manifest already pinned to {}".format(target_version))
        if meta_updates:
            success("Dry-run: {} mod meta.xml file(s) would be updated".format(len(meta_updates)))
            for item in meta_updates:
                detail(
                    "{}: {} -> {}".format(item["path"], item["current_version"] or "<missing>", target_version),
                    verbose=args.verbose,
                )
        detail("Source: {}".format(source), verbose=args.verbose)
        return

    if manifest_needs_update:
        save_wot_version_manifest(target_version)
        success("WoT version manifest updated: {} -> {}".format(current_version, target_version))
    else:
        success("WoT version manifest already pinned to {}".format(target_version))

    if meta_updates:
        _write_meta_updates(meta_updates, target_version)
        success("Updated mod meta.xml files: {}".format(len(meta_updates)))
        for item in meta_updates:
            detail(
                "{}: {} -> {}".format(item["path"], item["current_version"] or "<missing>", target_version),
                verbose=args.verbose,
            )
    else:
        success("All mod meta.xml files already pinned to {}".format(target_version))

    detail("Source: {}".format(source), verbose=args.verbose)


def main(argv=None):
    try:
        return _main(argv)
    except WotVersionError as exc:
        raise SystemExit(str(exc)) from None


if __name__ == "__main__":
    main()
