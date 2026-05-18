"""Config state and settings-template helpers for research-progress-bar."""
from __future__ import print_function, unicode_literals

import io
import json
import logging
import os
from numbers import Integral

from .constants import MOD_CONFIG_DIR_NAME
from .localization import get_text as _loc
from .localization import make_tooltip as _loc_tooltip
from .localization import set_language_override as _set_language_override

_logger = logging.getLogger('zanju.researchprogressbar')

try:
    _STRING_TYPES = (basestring,)
except NameError:
    _STRING_TYPES = (str,)

_config = {
    'enabled': True,
    'language': 'auto',
    'showTechTree': True,
    'showFieldMods': True,
    'showUpgrades': True,
    'eliteMode': 'on',
    'scaleformPrototypeEnabled': True,
}

_CONFIG_PERSISTED_KEYS = (
    'enabled',
    'language',
    'showTechTree',
    'showFieldMods',
    'showUpgrades',
    'eliteMode',
    'scaleformPrototypeEnabled',
)

_ELITE_MODE_ON = 'on'
_ELITE_MODE_CUSTOMIZATION_ONLY = 'customization_only'
_ELITE_MODE_OFF = 'off'
_ELITE_MODE_VALUES = (
    _ELITE_MODE_ON,
    _ELITE_MODE_CUSTOMIZATION_ONLY,
    _ELITE_MODE_OFF,
)
_ELITE_MODE_INDEX_BY_VALUE = dict(
    (value, index) for index, value in enumerate(_ELITE_MODE_VALUES)
)
_MODS_SETTINGS_SCHEMA_VERSION = 6
_MODS_SETTINGS_USER_KEYS = (
    'enabled',
    'showTechTree',
    'showFieldMods',
    'showUpgrades',
    'showEliteProgress',
)

_mods_settings_sync_in_progress = False


def _get_config_path():
    return os.path.join('mods', 'configs', MOD_CONFIG_DIR_NAME, 'config.json')


def _load_config():
    try:
        path = _get_config_path()
        if os.path.isfile(path):
            with io.open(path, 'r', encoding='utf-8') as fh:
                loaded = json.load(fh)
            if isinstance(loaded, dict):
                _config.update(loaded)
            _normalize_display_config()
            _logger.info('Config loaded from %s', path)
    except Exception:
        _logger.exception('Failed to load config, using defaults')
    _normalize_display_config()


def _normalize_elite_mode(value):
    if isinstance(value, bool):
        return _ELITE_MODE_ON if value else _ELITE_MODE_OFF
    if isinstance(value, Integral):
        index = int(value)
        if index >= 0 and index < len(_ELITE_MODE_VALUES):
            return _ELITE_MODE_VALUES[index]
        return _ELITE_MODE_ON
    if isinstance(value, _STRING_TYPES):
        normalized = value.strip().lower().replace('-', '_').replace(' ', '_')
        if normalized in _ELITE_MODE_INDEX_BY_VALUE:
            return normalized
        if normalized in ('customization', 'customisation', 'cosmetics_only'):
            return _ELITE_MODE_CUSTOMIZATION_ONLY
        if normalized in ('true', 'enabled'):
            return _ELITE_MODE_ON
        if normalized in ('false', 'disabled'):
            return _ELITE_MODE_OFF
    return _ELITE_MODE_ON


def _normalize_display_config():
    legacy_elite_value = _config.get(
        'showEliteProgress',
        _config.get('eliteMode', _ELITE_MODE_ON),
    )
    language = _config.get('language', 'auto')
    if not isinstance(language, _STRING_TYPES):
        language = 'auto'
    language = language.strip().lower().replace('-', '_') or 'auto'
    if language in ('client', 'default', 'system'):
        language = 'auto'
    _config['language'] = language
    for key in ('enabled', 'showTechTree', 'showFieldMods', 'showUpgrades'):
        _config[key] = bool(_config.get(key, True))
    _config['eliteMode'] = _normalize_elite_mode(
        _config.get('eliteMode', legacy_elite_value)
    )
    _set_language_override(_config.get('language', 'auto'))


def _build_mode_preferences():
    return {
        'showResearch': bool(_config.get('showTechTree', True)),
        'showFieldMods': bool(_config.get('showFieldMods', True)),
        'showUpgrades': bool(_config.get('showUpgrades', True)),
        'eliteMode': _normalize_elite_mode(_config.get('eliteMode', _ELITE_MODE_ON)),
    }


def _save_config():
    path = _get_config_path()
    data = {}
    try:
        if os.path.isfile(path):
            with io.open(path, 'r', encoding='utf-8') as fh:
                existing = json.load(fh)
            if isinstance(existing, dict):
                data.update(existing)
    except Exception:
        _logger.exception(
            'Failed to read existing config before save, rewriting %s',
            path,
        )
        data = {}

    try:
        directory = os.path.dirname(path)
        if directory and not os.path.isdir(directory):
            os.makedirs(directory)

        data['configVersion'] = data.get('configVersion', 1)
        data.pop('showEliteProgress', None)
        for key in _CONFIG_PERSISTED_KEYS:
            data[key] = _config.get(key)

        payload = json.dumps(data, indent=4, sort_keys=False)
        if not payload.endswith('\n'):
            payload += '\n'

        with io.open(path, 'w', encoding='utf-8') as fh:
            fh.write(payload)

        _logger.info('Config saved to %s', path)
    except Exception:
        _logger.exception('Failed to save config to %s', path)


def _build_mod_settings_state():
    return {
        'enabled': bool(_config.get('enabled', True)),
        'showTechTree': bool(_config.get('showTechTree', True)),
        'showFieldMods': bool(_config.get('showFieldMods', True)),
        'showUpgrades': bool(_config.get('showUpgrades', True)),
        'showEliteProgress': _ELITE_MODE_INDEX_BY_VALUE.get(
            _normalize_elite_mode(_config.get('eliteMode', _ELITE_MODE_ON)),
            0,
        ),
    }


def _mods_settings_native(value):
    if type(value).__name__ == 'unicode':
        return value.encode('utf-8')
    if isinstance(value, list):
        return [_mods_settings_native(item) for item in value]
    if isinstance(value, tuple):
        return tuple(_mods_settings_native(item) for item in value)
    if isinstance(value, dict):
        converted = {}
        try:
            items = value.iteritems()
        except AttributeError:
            items = value.items()
        for key, item in items:
            converted[_mods_settings_native(key)] = _mods_settings_native(item)
        return converted
    return value


def _build_mod_settings_template():
    settings = _build_mod_settings_state()
    return _mods_settings_native({
        'modDisplayName': _loc('MOD_NAME', "Zanju's Research Progress Bar"),
        'settingsVersion': _MODS_SETTINGS_SCHEMA_VERSION,
        'enabled': settings['enabled'],
        'column1': [
            {
                'type': 'CheckBox',
                'text': _loc('SETTING_RESEARCH', 'Research'),
                'tooltip': _loc_tooltip(
                    'TOOLTIP_RESEARCH_HEADER',
                    'TOOLTIP_RESEARCH_BODY',
                    'Research',
                    'Show XP progress toward the next researchable module or vehicle.',
                ),
                'value': settings['showTechTree'],
                'varName': 'showTechTree',
            },
            {
                'type': 'CheckBox',
                'text': _loc('SETTING_FIELD_MODS', 'Field Mods'),
                'tooltip': _loc_tooltip(
                    'TOOLTIP_FIELD_MODS_HEADER',
                    'TOOLTIP_FIELD_MODS_BODY',
                    'Field Mods',
                    'Show field modification progress for elite vehicles that support field modifications.',
                ),
                'value': settings['showFieldMods'],
                'varName': 'showFieldMods',
            },
            {
                'type': 'CheckBox',
                'text': _loc('SETTING_UPGRADES', 'Upgrades'),
                'tooltip': _loc_tooltip(
                    'TOOLTIP_UPGRADES_HEADER',
                    'TOOLTIP_UPGRADES_BODY',
                    'Upgrades',
                    'Show tier XI upgrade tree progress.',
                ),
                'value': settings['showUpgrades'],
                'varName': 'showUpgrades',
            },
            {
                'type': 'RadioButtonGroup',
                'text': _loc('SETTING_ELITE', 'Elite'),
                'tooltip': _loc_tooltip(
                    'TOOLTIP_ELITE_HEADER',
                    'TOOLTIP_ELITE_BODY',
                    'Elite',
                    '<b>On</b>: Show elite badges and tier XI customization elements.\n'
                    '<b>Customization only</b>: Show tier XI customization elements and hide elite badges.\n'
                    '<b>Off</b>: Hide elite progress entirely.',
                ),
                'options': [
                    {'label': _loc('SETTING_ELITE_OPTION_ON', 'On')},
                    {'label': _loc('SETTING_ELITE_OPTION_CUSTOMIZATION_ONLY', 'Customization only')},
                    {'label': _loc('SETTING_ELITE_OPTION_OFF', 'Off')},
                ],
                'value': settings['showEliteProgress'],
                'varName': 'showEliteProgress',
            },
        ],
    })


def _get_mods_settings_api():
    try:
        from gui.modsSettingsApi import g_modsSettingsApi
        return g_modsSettingsApi
    except Exception:
        return None


def _register_mod_settings(mod_id, on_config_changed=None):
    global _mods_settings_sync_in_progress

    def _on_mod_settings_changed(linkage, new_settings):
        if linkage != mod_id or _mods_settings_sync_in_progress:
            return
        if not isinstance(new_settings, dict):
            return

        changed_keys = []
        for key in _MODS_SETTINGS_USER_KEYS:
            if key not in new_settings:
                continue
            config_key = key
            if key == 'showEliteProgress':
                config_key = 'eliteMode'
                new_value = _normalize_elite_mode(new_settings.get(key))
            else:
                new_value = bool(new_settings.get(key))
            if _config.get(config_key) != new_value:
                _config[config_key] = new_value
                changed_keys.append(config_key)

        if not changed_keys:
            return

        _save_config()
        reason = 'mods_settings_api:{0}'.format(','.join(changed_keys))
        _logger.info('Applied ModsSettingsApi changes: %s', ', '.join(changed_keys))
        if callable(on_config_changed):
            try:
                on_config_changed(reason)
            except Exception:
                _logger.exception('Failed to apply external config change callback (%s)', reason)

    api = _get_mods_settings_api()
    if api is None:
        _logger.info('ModsSettingsApi not found; in-game settings are unavailable')
        return False

    try:
        api.setModTemplate(mod_id, _build_mod_settings_template(), _on_mod_settings_changed)
        _mods_settings_sync_in_progress = True
        try:
            api.updateModSettings(mod_id, _mods_settings_native(_build_mod_settings_state()))
        finally:
            _mods_settings_sync_in_progress = False
        _logger.info('ModsSettingsApi integration registered')
        return True
    except Exception:
        _mods_settings_sync_in_progress = False
        _logger.exception('Failed to register ModsSettingsApi integration')
        return False
