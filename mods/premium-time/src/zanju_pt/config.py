"""Config state and settings-template helpers for premium-time."""
from __future__ import print_function, unicode_literals

import io
import json
import logging
import os
from collections import OrderedDict
from numbers import Integral

from .constants import MOD_NAME
from .localization import get_text as _loc
from .localization import make_tooltip as _loc_tooltip
from .localization import set_language_override as _set_language_override
from .storage import atomic_write_text, resolve_mod_data_dir

_logger = logging.getLogger('zanju.premiumtime')

try:
    _STRING_TYPES = (basestring,)
except NameError:
    _STRING_TYPES = (str,)

_config = {
    'enabled': True,
    'language': 'auto',
    'showPremiumAccount': True,
    'showWotPlus': True,
    'hideWhenInactive': False,
    'corner': 'top_right',
}

# Frozen copy of the factory defaults, captured before _load_config mutates _config in place.
# The in-game settings template is built from these so the menu's per-mod Reset restores real
# defaults rather than the values present when the template was first registered.
_DEFAULT_CONFIG = dict(_config)

_CONFIG_PERSISTED_KEYS = (
    'enabled',
    'language',
    'showPremiumAccount',
    'showWotPlus',
    'hideWhenInactive',
    'corner',
)

_CONFIG_SAVE_KEY_ORDER = (
    '_comment',
    'configVersion',
    'enabled',
    '_language_comment',
    'language',
    'showPremiumAccount',
    'showWotPlus',
    'hideWhenInactive',
    '_corner_comment',
    'corner',
)

# Explanatory keys seeded into the self-created config so the AppData file stays readable for
# anyone who opens it by hand. Only the comment keys present in _CONFIG_SAVE_KEY_ORDER are used.
_CONFIG_COMMENTS = {
    '_comment': (
        'Auto-generated config for zanju.premiumtime. Stored in AppData so it survives '
        'modpack reinstalls; edited in-game via the mod settings menu and recreated with '
        'defaults if deleted.'
    ),
    '_language_comment': (
        'auto | <language-code>; runtime loads mods/configs/premium-time/i18n/<code>.yml '
        'with English fallback'
    ),
    '_corner_comment': 'top_right | top_left | bottom_right | bottom_left',
}

_CORNER_TOP_RIGHT = 'top_right'
_CORNER_TOP_LEFT = 'top_left'
_CORNER_BOTTOM_RIGHT = 'bottom_right'
_CORNER_BOTTOM_LEFT = 'bottom_left'
_CORNER_VALUES = (
    _CORNER_TOP_RIGHT,
    _CORNER_TOP_LEFT,
    _CORNER_BOTTOM_RIGHT,
    _CORNER_BOTTOM_LEFT,
)
_CORNER_INDEX_BY_VALUE = dict(
    (value, index) for index, value in enumerate(_CORNER_VALUES)
)

_MODS_SETTINGS_USER_KEYS = (
    'enabled',
    'showPremiumAccount',
    'showWotPlus',
    'hideWhenInactive',
    'corner',
)

_mods_settings_sync_in_progress = False


def _get_config_path():
    base_dir = resolve_mod_data_dir()
    if not base_dir:
        return None
    return os.path.join(base_dir, 'config.json')


def _load_config():
    path = _get_config_path()
    if path is None:
        _logger.warning('Config disabled: could not resolve AppData path; using defaults')
        _normalize_display_config()
        return

    if not os.path.isfile(path):
        # First run (or the file was deleted/wiped by a modpack reinstall): materialise the
        # defaults so the config self-heals and the user has a file to hand-edit.
        _normalize_display_config()
        _save_config()
        _logger.info('Config not found; created defaults at %s', path)
        return

    try:
        with io.open(path, 'r', encoding='utf-8') as fh:
            loaded = json.load(fh)
        if isinstance(loaded, dict):
            _config.update(loaded)
        _logger.info('Config loaded from %s', path)
    except Exception:
        _logger.exception('Failed to load config, using defaults')
    _normalize_display_config()


def _normalize_corner(value):
    if isinstance(value, Integral) and not isinstance(value, bool):
        index = int(value)
        if 0 <= index < len(_CORNER_VALUES):
            return _CORNER_VALUES[index]
        return _CORNER_TOP_RIGHT
    if isinstance(value, _STRING_TYPES):
        normalized = value.strip().lower().replace('-', '_').replace(' ', '_')
        if normalized in _CORNER_INDEX_BY_VALUE:
            return normalized
    return _CORNER_TOP_RIGHT


def _normalize_display_config():
    language = _config.get('language', 'auto')
    if not isinstance(language, _STRING_TYPES):
        language = 'auto'
    language = language.strip().lower().replace('-', '_') or 'auto'
    if language in ('client', 'default', 'system'):
        language = 'auto'
    _config['language'] = language

    for key in ('enabled', 'showPremiumAccount', 'showWotPlus', 'hideWhenInactive'):
        _config[key] = bool(_config.get(key, _DEFAULT_CONFIG[key]))

    _config['corner'] = _normalize_corner(_config.get('corner', _CORNER_TOP_RIGHT))
    _set_language_override(_config.get('language', 'auto'))


def _build_display_preferences():
    return {
        'showPremiumAccount': bool(_config.get('showPremiumAccount', True)),
        'showWotPlus': bool(_config.get('showWotPlus', True)),
        'hideWhenInactive': bool(_config.get('hideWhenInactive', False)),
        'corner': _normalize_corner(_config.get('corner', _CORNER_TOP_RIGHT)),
    }


def _save_config():
    path = _get_config_path()
    if path is None:
        return

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

    data['configVersion'] = data.get('configVersion', 1)
    for key in _CONFIG_PERSISTED_KEYS:
        data[key] = _config.get(key)
    for key, comment in _CONFIG_COMMENTS.items():
        data.setdefault(key, comment)

    ordered_data = OrderedDict()
    for key in _CONFIG_SAVE_KEY_ORDER:
        if key in data:
            ordered_data[key] = data[key]
    for key, value in data.items():
        if key not in ordered_data:
            ordered_data[key] = value

    payload = json.dumps(ordered_data, indent=4, sort_keys=False)
    if not payload.endswith('\n'):
        payload += '\n'

    if atomic_write_text(path, payload, _logger):
        _logger.info('Config saved to %s', path)


def _build_mod_settings_state(config=None):
    config = _config if config is None else config
    return {
        'enabled': bool(config.get('enabled', True)),
        'showPremiumAccount': bool(config.get('showPremiumAccount', True)),
        'showWotPlus': bool(config.get('showWotPlus', True)),
        'hideWhenInactive': bool(config.get('hideWhenInactive', False)),
        'corner': _CORNER_INDEX_BY_VALUE.get(
            _normalize_corner(config.get('corner', _CORNER_TOP_RIGHT)),
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


def _mods_settings_native_key(value):
    native_value = _mods_settings_native(value)
    if isinstance(native_value, _STRING_TYPES):
        return native_value
    return '{0}'.format(native_value)


def _build_mod_settings_template():
    # Build the template from factory defaults so the menu's per-mod Reset target is the real
    # defaults; the user's saved values are pushed separately via updateModSettings.
    settings = _build_mod_settings_state(_DEFAULT_CONFIG)
    return _mods_settings_native({
        'modDisplayName': MOD_NAME,
        'enabled': settings['enabled'],
        'column1': [
            {
                'type': 'CheckBox',
                'text': _loc('SETTING_SHOW_PREMIUM_ACCOUNT', 'Show Premium Account'),
                'tooltip': _loc_tooltip(
                    'SETTING_SHOW_PREMIUM_ACCOUNT',
                    'TOOLTIP_SHOW_PREMIUM_ACCOUNT_BODY',
                    'Show Premium Account',
                    'Show the remaining time on your WoT Premium Account.',
                ),
                'value': settings['showPremiumAccount'],
                'varName': 'showPremiumAccount',
            },
            {
                'type': 'CheckBox',
                'text': _loc('SETTING_SHOW_WOT_PLUS', 'Show WoT Plus'),
                'tooltip': _loc_tooltip(
                    'SETTING_SHOW_WOT_PLUS',
                    'TOOLTIP_SHOW_WOT_PLUS_BODY',
                    'Show WoT Plus',
                    'Show the remaining time on your WoT Plus / WoT Plus Pro subscription.',
                ),
                'value': settings['showWotPlus'],
                'varName': 'showWotPlus',
            },
            {
                'type': 'CheckBox',
                'text': _loc('SETTING_HIDE_WHEN_INACTIVE', 'Hide when inactive'),
                'tooltip': _loc_tooltip(
                    'SETTING_HIDE_WHEN_INACTIVE',
                    'TOOLTIP_HIDE_WHEN_INACTIVE_BODY',
                    'Hide when inactive',
                    'Hide the widget entirely when no premium subscription is active, '
                    'instead of showing an "inactive" line.',
                ),
                'value': settings['hideWhenInactive'],
                'varName': 'hideWhenInactive',
            },
            {
                'type': 'RadioButtonGroup',
                'text': _loc('SETTING_CORNER', 'Screen corner'),
                'tooltip': _loc_tooltip(
                    'SETTING_CORNER',
                    'TOOLTIP_CORNER_BODY',
                    'Screen corner',
                    'Choose which corner of the hangar the widget is anchored to.',
                ),
                'options': [
                    {'label': _loc('SETTING_CORNER_TOP_RIGHT', 'Top right')},
                    {'label': _loc('SETTING_CORNER_TOP_LEFT', 'Top left')},
                    {'label': _loc('SETTING_CORNER_BOTTOM_RIGHT', 'Bottom right')},
                    {'label': _loc('SETTING_CORNER_BOTTOM_LEFT', 'Bottom left')},
                ],
                'value': settings['corner'],
                'varName': 'corner',
            },
        ],
    })


def _get_mods_settings_api():
    try:
        from gui.aslainMenu import g_modsSettingsApi
        return g_modsSettingsApi
    except Exception:
        return None


def _register_mod_settings(mod_id, on_config_changed=None):
    global _mods_settings_sync_in_progress

    native_mod_id = _mods_settings_native_key(mod_id)

    def _on_mod_settings_changed(linkage, new_settings):
        if _mods_settings_native_key(linkage) != native_mod_id or _mods_settings_sync_in_progress:
            return
        if not isinstance(new_settings, dict):
            return

        changed_keys = []
        for key in _MODS_SETTINGS_USER_KEYS:
            if key not in new_settings:
                continue
            config_key = key
            if key == 'corner':
                new_value = _normalize_corner(new_settings.get(key))
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
        _logger.info('Aslain ModsSettings menu (gui.aslainMenu) not found; in-game settings are unavailable')
        return False

    try:
        api.setModTemplate(native_mod_id, _build_mod_settings_template(), _on_mod_settings_changed)
        _mods_settings_sync_in_progress = True
        try:
            api.updateModSettings(native_mod_id, _mods_settings_native(_build_mod_settings_state()))
        finally:
            _mods_settings_sync_in_progress = False
        _logger.info('ModsSettingsApi integration registered')
        return True
    except Exception:
        _mods_settings_sync_in_progress = False
        _logger.exception('Failed to register ModsSettingsApi integration')
        return False
