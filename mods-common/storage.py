"""Shared on-disk storage helpers: AppData path resolution and atomic writes.

A mod keeps its files in its own folder under a shared AppData parent, so the modpack never
wipes them on reinstall. The parent is in the folder where other mods of the game keep their
settings too, under our name. For example:

    %APPDATA%/Wargaming.net/WorldOfTanks/mods/Zanju/directives-helper/window.json
    %APPDATA%/Wargaming.net/WorldOfTanks/mods/Zanju/research-progress-bar/{config.json, cache.json}

Each mod gives its own folder name to `resolve_mod_data_dir`. The name decides where the
player's settings are, so it must never change.

Earlier releases (campaign-tracker 1.2.3, directives-helper 1.0.7, research-progress-bar 1.4.6
and before) kept these folders in `%APPDATA%/zanju_wot_mods_cache/`. The first
time a mod asks for its folder in a session, and the new folder does not exist yet, the mod copies
its old folder there, so the player keeps the settings. The old folder stays as it was, so an older
release of the mod still finds its files there.
"""
from __future__ import absolute_import, print_function, unicode_literals

import io
import logging
import os
import shutil

from ._mod_meta import MOD_ID

try:
    _text_type = unicode
except NameError:
    _text_type = str

# Shared parent for every Zanju WoT mod's AppData data, below AppData; the per-mod subfolder
# keeps this mod's files separate from any other mod that uses the same parent.
_DATA_ROOT_PARTS = ('Wargaming.net', 'WorldOfTanks', 'mods', 'Zanju')
# The parent of the earlier releases, directly in AppData. Read only, to copy from.
_LEGACY_ROOT_DIR_NAME = 'zanju_wot_mods_cache'

# The folders already checked for a copy from the old parent in this session.
_checked = set()


def resolve_mod_data_dir(dir_name):
    base_dir = resolve_appdata_base_dir()
    if not base_dir:
        return None

    path = os.path.join(base_dir, *(_DATA_ROOT_PARTS + (dir_name,)))
    if path not in _checked:
        _checked.add(path)
        copy_legacy_dir(os.path.join(base_dir, _LEGACY_ROOT_DIR_NAME, dir_name), path)
    return path


def copy_legacy_dir(old_dir, new_dir):
    """Copy the folder of an older release to the new place, when only the old one exists.

    Returns True when it copied. A copy that fails is removed again, so the next session tries
    again, and the mod meanwhile starts with its defaults.
    """
    if os.path.exists(new_dir) or not os.path.isdir(old_dir):
        return False
    logger = logging.getLogger(MOD_ID)
    try:
        shutil.copytree(old_dir, new_dir)
    except Exception:
        logger.exception('Failed to copy the settings from %s to %s', old_dir, new_dir)
        shutil.rmtree(new_dir, ignore_errors=True)
        return False
    logger.info('Copied the settings of an older release from %s to %s', old_dir, new_dir)
    return True


def resolve_appdata_base_dir():
    for env_name in ('APPDATA', 'LOCALAPPDATA'):
        value = _normalize_path(os.environ.get(env_name))
        if value:
            return value

    user_profile = _normalize_path(os.environ.get('USERPROFILE'))
    if not user_profile:
        return None

    return os.path.join(user_profile, 'AppData', 'Roaming')


def atomic_write_text(path, text, logger):
    # Atomic write: serialise to a temp file (flush+fsync), then replace the target in one
    # step, so a crash mid-write can never leave a truncated/corrupt file. os.rename is atomic
    # on POSIX; on Windows Py2.7 it cannot overwrite, so fall back to remove-then-rename - the
    # live file is still never partially written, since the full content lands in the temp file
    # first.
    tmp = path + '.tmp'
    try:
        directory = os.path.dirname(path)
        if directory and not os.path.isdir(directory):
            os.makedirs(directory)
        with io.open(tmp, 'w', encoding='utf-8') as fh:
            fh.write(text)
            try:
                fh.flush()
                os.fsync(fh.fileno())
            except Exception:
                pass
        try:
            os.rename(tmp, path)
        except OSError:
            if os.path.exists(path):
                os.remove(path)
            os.rename(tmp, path)
        return True
    except Exception:
        logger.exception('Failed to write %s', path)
        try:
            if os.path.exists(tmp):
                os.remove(tmp)
        except Exception:
            pass
        return False


def _normalize_path(value):
    text = _normalize_text(value)
    if text is None:
        return None
    return os.path.normpath(text)


def _normalize_text(value):
    if value is None:
        return None

    try:
        text = value if isinstance(value, _text_type) else _text_type(value)
    except Exception:
        return None

    text = text.strip()
    if not text:
        return None
    return text
