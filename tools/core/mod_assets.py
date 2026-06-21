"""Shared filesystem and config/i18n staging helpers for build and deploy.

Both the packaging (build) and the dev-deploy (deploy) flows copy the same mod
source trees and resolve the same `config.template.json` / `config/` and `i18n/`
layouts. These helpers keep that one definition.
"""

from __future__ import annotations

import os
import shutil


def copy_tree_contents(src_dir, dst_dir):
    """Copy the contents of src_dir into dst_dir (merging into existing dirs)."""
    if not os.path.isdir(src_dir):
        return

    os.makedirs(dst_dir, exist_ok=True)
    for name in sorted(os.listdir(src_dir)):
        src_path = os.path.join(src_dir, name)
        dst_path = os.path.join(dst_dir, name)
        if os.path.isdir(src_path):
            shutil.copytree(src_path, dst_path, dirs_exist_ok=True)
        else:
            dst_parent = os.path.dirname(dst_path)
            if dst_parent:
                os.makedirs(dst_parent, exist_ok=True)
            shutil.copy2(src_path, dst_path)


def copy_file(src_path, dst_path):
    dst_parent = os.path.dirname(dst_path)
    if dst_parent:
        os.makedirs(dst_parent, exist_ok=True)
    shutil.copy2(src_path, dst_path)


def directory_has_entries(path):
    return os.path.isdir(path) and bool(os.listdir(path))


def resolve_config_source(mod_dir):
    """Resolve a mod's config source, or None.

    Returns ("file", path) for a flat config.template.json, ("dir", path) for a
    legacy config/ directory, and raises when both are present.
    """
    flat_config_path = os.path.join(mod_dir, "config.template.json")
    legacy_config_dir = os.path.join(mod_dir, "config")

    has_flat_config = os.path.isfile(flat_config_path)
    has_legacy_config_dir = directory_has_entries(legacy_config_dir)

    if has_flat_config and has_legacy_config_dir:
        raise RuntimeError(
            "{} defines both config.template.json and config/; keep exactly one config source.".format(
                os.path.basename(mod_dir)
            )
        )
    if has_flat_config:
        return "file", flat_config_path
    if has_legacy_config_dir:
        return "dir", legacy_config_dir
    return None


def resolve_i18n_source(mod_dir):
    i18n_dir = os.path.join(mod_dir, "i18n")
    if directory_has_entries(i18n_dir):
        return i18n_dir
    return None


def stage_config_source(mod_dir, dst_config_dir):
    """Stage a mod's config into dst_config_dir. Returns the source path or None."""
    config_source = resolve_config_source(mod_dir)
    if not config_source:
        return None

    source_kind, source_path = config_source
    if source_kind == "dir":
        copy_tree_contents(source_path, dst_config_dir)
    else:
        copy_file(source_path, os.path.join(dst_config_dir, "config.json"))
    return source_path


def stage_i18n_source(mod_dir, dst_i18n_dir):
    """Stage a mod's i18n/ tree into dst_i18n_dir. Returns the source path or None."""
    i18n_source = resolve_i18n_source(mod_dir)
    if not i18n_source:
        return None

    copy_tree_contents(i18n_source, dst_i18n_dir)
    return i18n_source
