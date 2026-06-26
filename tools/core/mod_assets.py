"""Shared filesystem and i18n staging helpers for build and deploy.

Both the packaging (build) and the dev-deploy (deploy) flows copy the same mod
source trees and resolve the same `i18n/` layout. These helpers keep that one
definition.

Mods do not ship a config file: each mod self-creates its config in AppData on
first run (see its `src/.../storage.py`), so settings survive modpack reinstalls.
Only `i18n/` is staged into `mods/configs/<mod-name>/`.
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


def directory_has_entries(path):
    return os.path.isdir(path) and bool(os.listdir(path))


def resolve_i18n_source(mod_dir):
    i18n_dir = os.path.join(mod_dir, "i18n")
    if directory_has_entries(i18n_dir):
        return i18n_dir
    return None


def stage_i18n_source(mod_dir, dst_i18n_dir):
    """Stage a mod's i18n/ tree into dst_i18n_dir. Returns the source path or None."""
    i18n_source = resolve_i18n_source(mod_dir)
    if not i18n_source:
        return None

    copy_tree_contents(i18n_source, dst_i18n_dir)
    return i18n_source
