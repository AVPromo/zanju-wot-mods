from __future__ import print_function, unicode_literals

import io
import json
import os
from collections import OrderedDict

from .storage import atomic_write_text, resolve_mod_data_dir

try:
    _text_type = unicode
except NameError:
    _text_type = str

_STATE_SCHEMA_VERSION = 1
_STATE_FILE_NAME = 'cache.json'
_MODE_SELECTION_SECTION_KEY = 'modeSelection'
_MODE_SELECTION_VEHICLES_KEY = 'vehicles'


class ModeSelectionState(object):
    def __init__(self):
        self._path = _resolve_state_path()
        self._dirty = False
        self._loaded = False
        self._vehicles = {}

    def load(self, logger):
        if self._loaded:
            return

        self._loaded = True
        if self._path is None:
            logger.warning('Mode selection state disabled: could not resolve AppData cache path')
            return

        logger.info('Mode selection state path: %s', self._path)

        if not os.path.isfile(self._path):
            logger.info('Mode selection state file not found; starting with empty cache')
            return

        try:
            with io.open(self._path, 'r', encoding='utf-8') as fh:
                data = json.load(fh)
        except Exception:
            logger.exception(
                'Failed to load mode selection state from %s; continuing with empty cache',
                self._path,
            )
            return

        if not isinstance(data, dict):
            logger.warning(
                'Ignoring mode selection state from %s: expected JSON object root',
                self._path,
            )
            return

        mode_selection = data.get(_MODE_SELECTION_SECTION_KEY)
        if not isinstance(mode_selection, dict):
            logger.warning(
                'Ignoring mode selection state from %s: missing %s object',
                self._path,
                _MODE_SELECTION_SECTION_KEY,
            )
            return

        vehicles = mode_selection.get(_MODE_SELECTION_VEHICLES_KEY)
        if not isinstance(vehicles, dict):
            logger.warning(
                'Ignoring mode selection state from %s: missing %s.%s object',
                self._path,
                _MODE_SELECTION_SECTION_KEY,
                _MODE_SELECTION_VEHICLES_KEY,
            )
            return

        self._vehicles = _normalize_vehicle_modes(vehicles)
        self._dirty = False
        if len(self._vehicles) != len(vehicles):
            logger.warning(
                'Loaded mode selection state from %s with %d invalid entries ignored',
                self._path,
                len(vehicles) - len(self._vehicles),
            )
        logger.info('Mode selection state loaded: vehicles=%d', len(self._vehicles))

    def get_mode(self, vehicle_int_cd):
        vehicle_key = _normalize_vehicle_key(vehicle_int_cd)
        if vehicle_key is None:
            return None
        return self._vehicles.get(vehicle_key)

    def set_mode(self, vehicle_int_cd, mode_id):
        vehicle_key = _normalize_vehicle_key(vehicle_int_cd)
        normalized_mode_id = _normalize_mode_id(mode_id)
        if vehicle_key is None or normalized_mode_id is None:
            return False

        if self._vehicles.get(vehicle_key) == normalized_mode_id:
            return False

        self._vehicles[vehicle_key] = normalized_mode_id
        self._dirty = True
        return True

    def save(self, logger):
        if self._path is None:
            return False

        if not self._dirty:
            return True

        payload = OrderedDict()
        payload['schemaVersion'] = _STATE_SCHEMA_VERSION
        payload[_MODE_SELECTION_SECTION_KEY] = OrderedDict()
        payload[_MODE_SELECTION_SECTION_KEY][_MODE_SELECTION_VEHICLES_KEY] = OrderedDict()
        for vehicle_key in _sorted_vehicle_keys(self._vehicles):
            payload[_MODE_SELECTION_SECTION_KEY][_MODE_SELECTION_VEHICLES_KEY][vehicle_key] = (
                self._vehicles[vehicle_key]
            )

        text = json.dumps(payload, indent=4, sort_keys=False)
        if not text.endswith('\n'):
            text += '\n'
        if not atomic_write_text(self._path, text, logger):
            return False

        self._dirty = False
        logger.info('Mode selection state saved: vehicles=%d', len(self._vehicles))
        return True


def _resolve_state_path():
    base_dir = resolve_mod_data_dir()
    if not base_dir:
        return None

    return os.path.join(base_dir, _STATE_FILE_NAME)


def _normalize_vehicle_modes(value):
    normalized = {}
    try:
        items = value.iteritems()
    except AttributeError:
        items = value.items()

    for vehicle_key, mode_id in items:
        normalized_key = _normalize_vehicle_key(vehicle_key)
        normalized_mode_id = _normalize_mode_id(mode_id)
        if normalized_key is None or normalized_mode_id is None:
            continue
        normalized[normalized_key] = normalized_mode_id

    return normalized


def _sorted_vehicle_keys(vehicle_modes):
    def _sort_key(value):
        if value.isdigit():
            return (0, int(value))
        return (1, value)

    return sorted(vehicle_modes.keys(), key=_sort_key)


def _normalize_vehicle_key(value):
    return _normalize_text(value)


def _normalize_mode_id(value):
    return _normalize_text(value)


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
