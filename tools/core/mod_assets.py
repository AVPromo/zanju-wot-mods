"""Shared filesystem helpers for staging mod resource trees during build.

The packaging (build) flow copies mod source trees, including the `i18n/` layout,
into the runtime package shape. These helpers keep that copy logic in one place.

Mods ship no loose files alongside the package: each mod self-creates its config
in AppData on first run (see its `src/.../storage.py`), and `i18n/*.yml` is bundled
inside the `.wotmod` at `res/mods/<id>/text/` rather than staged into a config folder.
"""

from __future__ import annotations

import os
import shutil


def copy_tree_contents(src_dir, dst_dir, ignore_names=()):
    """Copy the contents of src_dir into dst_dir (merging into existing dirs).

    Top-level entries whose name is in ignore_names are skipped.
    """
    if not os.path.isdir(src_dir):
        return

    os.makedirs(dst_dir, exist_ok=True)
    for name in sorted(os.listdir(src_dir)):
        if name in ignore_names:
            continue
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
