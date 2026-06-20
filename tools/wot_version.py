"""Shared WoT client version helpers for build/deploy/cleanup tooling."""

from __future__ import annotations

import json
import os
import re
import xml.etree.ElementTree as ET

from .paths import WOT_VERSION_MANIFEST_PATH

WOT_VERSION_SCHEMA_VERSION = 1
_WOT_VERSION_RE = re.compile(r"(\d+\.\d+\.\d+\.\d+)")


class WotVersionError(RuntimeError):
    """Raised when WoT version metadata is missing, malformed, or inconsistent."""


def _normalize_version(value, label):
    text = "{}".format(value or "").strip()
    if not _WOT_VERSION_RE.fullmatch(text):
        raise WotVersionError("{} must look like X.Y.Z.W (got: {})".format(label, value))
    return text


def load_wot_version_manifest(path=WOT_VERSION_MANIFEST_PATH):
    if not os.path.isfile(path):
        raise WotVersionError("WoT version manifest not found: {}".format(path))

    with open(path, "r", encoding="utf-8") as fh:
        manifest = json.load(fh)

    if not isinstance(manifest, dict):
        raise WotVersionError("WoT version manifest must be a JSON object: {}".format(path))

    schema_version = manifest.get("schemaVersion")
    if schema_version != WOT_VERSION_SCHEMA_VERSION:
        raise WotVersionError("Unsupported WoT version manifest schemaVersion '{}' in {}".format(schema_version, path))

    wot_client_version = _normalize_version(manifest.get("wotClientVersion"), "wotClientVersion")
    return {"schemaVersion": schema_version, "wotClientVersion": wot_client_version}


def save_wot_version_manifest(wot_client_version, path=WOT_VERSION_MANIFEST_PATH):
    version = _normalize_version(wot_client_version, "wotClientVersion")
    manifest = {
        "schemaVersion": WOT_VERSION_SCHEMA_VERSION,
        "wotClientVersion": version,
    }
    parent = os.path.dirname(path)
    if parent:
        os.makedirs(parent, exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(manifest, fh, indent=2, sort_keys=False)
        fh.write("\n")


def parse_version_xml(game_dir):
    version_xml_path = os.path.join(game_dir, "version.xml")
    if not os.path.isfile(version_xml_path):
        raise WotVersionError("version.xml was not found in WoT directory: {}".format(game_dir))

    root = ET.parse(version_xml_path).getroot()
    raw_text = (root.findtext("version", "") or "").strip()
    match = _WOT_VERSION_RE.search(raw_text)
    if not match:
        raise WotVersionError("Could not parse WoT client version from {}".format(version_xml_path))
    return match.group(1)


def resolve_target_wot_version(env, require_game_dir):
    expected_version = load_wot_version_manifest()["wotClientVersion"]
    if not require_game_dir:
        # Build is environment-agnostic: the pinned manifest version is authoritative
        # and no local game install is needed (CI, the toolchain container, etc.). Do
        # not touch WOT_GAME_DIR here — it may be a host path that is not visible in
        # the container, or unset.
        return expected_version

    game_dir = "{}".format((env or {}).get("WOT_GAME_DIR", "")).strip()
    if not game_dir:
        raise WotVersionError("WOT_GAME_DIR is required for this command")

    if not os.path.isdir(game_dir):
        raise WotVersionError("WOT_GAME_DIR does not exist: {}".format(game_dir))

    installed_version = parse_version_xml(game_dir)
    if installed_version != expected_version:
        raise WotVersionError(
            "WoT version mismatch: manifest={}, installed={}. "
            "Run wot_mods_update_wot_version_manifest to refresh the manifest pins.".format(
                expected_version,
                installed_version,
            )
        )
    return expected_version
