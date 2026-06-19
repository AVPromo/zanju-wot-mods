"""Config state and settings-template helpers for research-progress-bar."""
from __future__ import print_function, unicode_literals

import io
import json
import logging
import os
from collections import OrderedDict
from numbers import Integral

from .constants import MOD_CONFIG_DIR_NAME, MOD_NAME
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
    'showResearchReminder': True,
    'showAcceleratedCrewTrainingReminder': True,
    'researchMode': 'hypothetical_t11',
    'upgradesMode': 'on',
    'fieldModsMode': 'always',
    'eliteMode': 'on',
    'scaleformPrototypeEnabled': True,
}

_CONFIG_PERSISTED_KEYS = (
    'enabled',
    'language',
    'showResearchReminder',
    'showAcceleratedCrewTrainingReminder',
    'researchMode',
    'upgradesMode',
    'fieldModsMode',
    'eliteMode',
    'scaleformPrototypeEnabled',
)

_CONFIG_SAVE_KEY_ORDER = (
    '_comment',
    'configVersion',
    'enabled',
    '_language_comment',
    'language',
    'showResearchReminder',
    'showAcceleratedCrewTrainingReminder',
    '_researchMode_comment',
    'researchMode',
    '_upgradesMode_comment',
    'upgradesMode',
    '_fieldModsMode_comment',
    'fieldModsMode',
    '_eliteMode_comment',
    'eliteMode',
    '_scaleformPrototypeEnabled_comment',
    'scaleformPrototypeEnabled',
)

_FIELD_MODS_MODE_ALWAYS = 'always'
_FIELD_MODS_MODE_UNTIL_COMPLETE = 'until_complete'
_FIELD_MODS_MODE_OFF = 'off'
_FIELD_MODS_MODE_VALUES = (
    _FIELD_MODS_MODE_ALWAYS,
    _FIELD_MODS_MODE_UNTIL_COMPLETE,
    _FIELD_MODS_MODE_OFF,
)
_FIELD_MODS_MODE_INDEX_BY_VALUE = dict(
    (value, index) for index, value in enumerate(_FIELD_MODS_MODE_VALUES)
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

_RESEARCH_MODE_HYPOTHETICAL_T11 = 'hypothetical_t11'
_RESEARCH_MODE_REAL_ONLY = 'real_only'
_RESEARCH_MODE_OFF = 'off'
_RESEARCH_MODE_VALUES = (
    _RESEARCH_MODE_HYPOTHETICAL_T11,
    _RESEARCH_MODE_REAL_ONLY,
    _RESEARCH_MODE_OFF,
)
_RESEARCH_MODE_INDEX_BY_VALUE = dict(
    (value, index) for index, value in enumerate(_RESEARCH_MODE_VALUES)
)

_UPGRADES_MODE_ON = 'on'
_UPGRADES_MODE_OFF = 'off'
_UPGRADES_MODE_VALUES = (
    _UPGRADES_MODE_ON,
    _UPGRADES_MODE_OFF,
)
_UPGRADES_MODE_INDEX_BY_VALUE = dict(
    (value, index) for index, value in enumerate(_UPGRADES_MODE_VALUES)
)

_MODS_SETTINGS_USER_KEYS = (
    'enabled',
    'showResearchReminder',
    'showAcceleratedCrewTrainingReminder',
    'showResearchMode',
    'showUpgradesMode',
    'showFieldModsProgress',
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


def _normalize_field_mods_mode(value):
    if isinstance(value, bool):
        return _FIELD_MODS_MODE_UNTIL_COMPLETE if value else _FIELD_MODS_MODE_OFF
    if isinstance(value, Integral):
        index = int(value)
        if index >= 0 and index < len(_FIELD_MODS_MODE_VALUES):
            return _FIELD_MODS_MODE_VALUES[index]
        return _FIELD_MODS_MODE_ALWAYS
    if isinstance(value, _STRING_TYPES):
        normalized = value.strip().lower().replace('-', '_').replace(' ', '_')
        if normalized in _FIELD_MODS_MODE_INDEX_BY_VALUE:
            return normalized
        if normalized in ('untilcomplete', 'until_done', 'current'):
            return _FIELD_MODS_MODE_UNTIL_COMPLETE
        if normalized in ('true', 'enabled', 'on'):
            return _FIELD_MODS_MODE_UNTIL_COMPLETE
        if normalized in ('false', 'disabled'):
            return _FIELD_MODS_MODE_OFF
    return _FIELD_MODS_MODE_ALWAYS


def _normalize_research_mode(value):
    if isinstance(value, bool):
        return _RESEARCH_MODE_HYPOTHETICAL_T11 if value else _RESEARCH_MODE_OFF
    if isinstance(value, Integral):
        index = int(value)
        if index >= 0 and index < len(_RESEARCH_MODE_VALUES):
            return _RESEARCH_MODE_VALUES[index]
        return _RESEARCH_MODE_HYPOTHETICAL_T11
    if isinstance(value, _STRING_TYPES):
        normalized = value.strip().lower().replace('-', '_').replace(' ', '_')
        if normalized in _RESEARCH_MODE_INDEX_BY_VALUE:
            return normalized
        if normalized in ('real', 'realresearch', 'real_items', 'realonly'):
            return _RESEARCH_MODE_REAL_ONLY
        if normalized in ('false', 'disabled'):
            return _RESEARCH_MODE_OFF
    return _RESEARCH_MODE_HYPOTHETICAL_T11


def _normalize_upgrades_mode(value):
    if isinstance(value, bool):
        return _UPGRADES_MODE_ON if value else _UPGRADES_MODE_OFF
    if isinstance(value, Integral):
        index = int(value)
        if index >= 0 and index < len(_UPGRADES_MODE_VALUES):
            return _UPGRADES_MODE_VALUES[index]
        return _UPGRADES_MODE_ON
    if isinstance(value, _STRING_TYPES):
        normalized = value.strip().lower().replace('-', '_').replace(' ', '_')
        if normalized in _UPGRADES_MODE_INDEX_BY_VALUE:
            return normalized
        if normalized in ('true', 'enabled'):
            return _UPGRADES_MODE_ON
        if normalized in ('false', 'disabled'):
            return _UPGRADES_MODE_OFF
    return _UPGRADES_MODE_ON


def _normalize_display_config():
    legacy_field_mods_value = _config.get(
        'showFieldModsProgress',
        _config.get('fieldModsMode', _config.get('showFieldMods', _FIELD_MODS_MODE_ALWAYS)),
    )
    legacy_elite_value = _config.get(
        'showEliteProgress',
        _config.get('eliteMode', _ELITE_MODE_ON),
    )
    legacy_show_research = bool(_config.get('showTechTree', True))
    legacy_show_hypothetical_t11 = bool(_config.get('showHypotheticalTier11InResearch', True))
    legacy_show_upgrades = bool(_config.get('showUpgrades', True))
    language = _config.get('language', 'auto')
    if not isinstance(language, _STRING_TYPES):
        language = 'auto'
    language = language.strip().lower().replace('-', '_') or 'auto'
    if language in ('client', 'default', 'system'):
        language = 'auto'
    _config['language'] = language
    for key in (
            'enabled',
            'showResearchReminder',
            'showAcceleratedCrewTrainingReminder'):
        _config[key] = bool(_config.get(key, True))
    legacy_research_mode = _RESEARCH_MODE_OFF
    if legacy_show_research:
        legacy_research_mode = (
            _RESEARCH_MODE_HYPOTHETICAL_T11 if legacy_show_hypothetical_t11 else _RESEARCH_MODE_REAL_ONLY
        )
    _config['researchMode'] = _normalize_research_mode(
        _config.get('researchMode', legacy_research_mode)
    )
    _config['upgradesMode'] = _normalize_upgrades_mode(
        _config.get('upgradesMode', legacy_show_upgrades)
    )
    _config['fieldModsMode'] = _normalize_field_mods_mode(
        _config.get('fieldModsMode', legacy_field_mods_value)
    )
    _config['eliteMode'] = _normalize_elite_mode(
        _config.get('eliteMode', legacy_elite_value)
    )
    _set_language_override(_config.get('language', 'auto'))


def _build_mode_preferences():
    research_mode = _normalize_research_mode(
        _config.get('researchMode', _RESEARCH_MODE_HYPOTHETICAL_T11)
    )
    upgrades_mode = _normalize_upgrades_mode(_config.get('upgradesMode', _UPGRADES_MODE_ON))
    return {
        'showResearchReminder': bool(_config.get('showResearchReminder', True)),
        'showAcceleratedCrewTrainingReminder': bool(
            _config.get('showAcceleratedCrewTrainingReminder', True)
        ),
        'showResearch': research_mode != _RESEARCH_MODE_OFF,
        'showUpgrades': upgrades_mode == _UPGRADES_MODE_ON,
        'fieldModsMode': _normalize_field_mods_mode(
            _config.get('fieldModsMode', _FIELD_MODS_MODE_ALWAYS)
        ),
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
        data.pop('showTechTree', None)
        data.pop('showHypotheticalTier11InResearch', None)
        data.pop('showUpgrades', None)
        data.pop('showFieldMods', None)
        data.pop('showFieldModsProgress', None)
        data.pop('showEliteProgress', None)
        for key in _CONFIG_PERSISTED_KEYS:
            data[key] = _config.get(key)

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

        with io.open(path, 'w', encoding='utf-8') as fh:
            fh.write(payload)

        _logger.info('Config saved to %s', path)
    except Exception:
        _logger.exception('Failed to save config to %s', path)


def _build_mod_settings_state():
    research_mode = _normalize_research_mode(
        _config.get('researchMode', _RESEARCH_MODE_HYPOTHETICAL_T11)
    )
    upgrades_mode = _normalize_upgrades_mode(_config.get('upgradesMode', _UPGRADES_MODE_ON))
    return {
        'enabled': bool(_config.get('enabled', True)),
        'showResearchReminder': bool(_config.get('showResearchReminder', True)),
        'showAcceleratedCrewTrainingReminder': bool(
            _config.get('showAcceleratedCrewTrainingReminder', True)
        ),
        'showResearchMode': _RESEARCH_MODE_INDEX_BY_VALUE.get(research_mode, 0),
        'showUpgradesMode': _UPGRADES_MODE_INDEX_BY_VALUE.get(upgrades_mode, 0),
        'showFieldModsProgress': _FIELD_MODS_MODE_INDEX_BY_VALUE.get(
            _normalize_field_mods_mode(_config.get('fieldModsMode', _FIELD_MODS_MODE_ALWAYS)),
            0,
        ),
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


def _mods_settings_native_key(value):
    native_value = _mods_settings_native(value)
    if isinstance(native_value, _STRING_TYPES):
        return native_value
    return '{0}'.format(native_value)


def _build_mod_settings_template():
    settings = _build_mod_settings_state()
    return _mods_settings_native({
        'modDisplayName': MOD_NAME,
        'enabled': settings['enabled'],
        'column1': [
            {
                'type': 'CheckBox',
                'text': _loc('SETTING_RESEARCH_REMINDER', 'Show research reminder'),
                'tooltip': _loc_tooltip(
                    'SETTING_RESEARCH_REMINDER',
                    'TOOLTIP_RESEARCH_REMINDER_BODY',
                    'Research reminder',
                    'Show the separate "Research now!" reminder above the mode buttons.',
                ),
                'value': settings['showResearchReminder'],
                'varName': 'showResearchReminder',
            },
            {
                'type': 'CheckBox',
                'text': _loc('SETTING_ACCELERATED_CREW_TRAINING_REMINDER', 'Show accelerated crew training reminder'),
                'tooltip': _loc_tooltip(
                    'SETTING_ACCELERATED_CREW_TRAINING_REMINDER',
                    'TOOLTIP_ACCELERATED_CREW_TRAINING_REMINDER_BODY',
                    'Accelerated crew training reminder',
                    'Show the separate accelerated crew training reminder above the mode buttons.',
                ),
                'value': settings['showAcceleratedCrewTrainingReminder'],
                'varName': 'showAcceleratedCrewTrainingReminder',
            },
            {
                'type': 'RadioButtonGroup',
                'text': _loc('SETTING_RESEARCH', 'Research'),
                'tooltip': _loc_tooltip(
                    'SETTING_RESEARCH',
                    'TOOLTIP_RESEARCH_BODY',
                    'Research',
                    'Show XP progress toward the next researchable module or vehicle.',
                ),
                'options': [
                    {'label': _loc('SETTING_HYPOTHETICAL_TIER11_IN_RESEARCH', 'Show hypothetical tier 11 in research')},
                    {'label': _loc('SETTING_RESEARCH_OPTION_REAL_ONLY', 'Show only real research items')},
                    {'label': _loc('SETTING_OPTION_OFF', 'Off')},
                ],
                'value': settings['showResearchMode'],
                'varName': 'showResearchMode',
            },
            {
                'type': 'RadioButtonGroup',
                'text': _loc('SETTING_UPGRADES', 'Upgrades'),
                'tooltip': _loc_tooltip(
                    'SETTING_UPGRADES',
                    'TOOLTIP_UPGRADES_BODY',
                    'Upgrades',
                    'Show tier XI upgrade tree progress.',
                ),
                'options': [
                    {'label': _loc('SETTING_OPTION_ON', 'On')},
                    {'label': _loc('SETTING_OPTION_OFF', 'Off')},
                ],
                'value': settings['showUpgradesMode'],
                'varName': 'showUpgradesMode',
            },
            {
                'type': 'RadioButtonGroup',
                'text': _loc('SETTING_FIELD_MODS', 'Field Mods'),
                'tooltip': _loc_tooltip(
                    'TOOLTIP_FIELD_MODS_HEADER',
                    'TOOLTIP_FIELD_MODS_BODY',
                    'Field Mods',
                    '<b>Always show</b>: Keep the field mods mode available even after '
                    'all field modifications are complete.\n'
                    '<b>Until complete</b>: Hide the field mods mode once all field modifications are complete.\n'
                    '<b>Off</b>: Hide field mods entirely.',
                ),
                'options': [
                    {'label': _loc('SETTING_FIELD_MODS_OPTION_ALWAYS', 'Always show')},
                    {'label': _loc('SETTING_FIELD_MODS_OPTION_UNTIL_COMPLETE', 'Until complete')},
                    {'label': _loc('SETTING_OPTION_OFF', 'Off')},
                ],
                'value': settings['showFieldModsProgress'],
                'varName': 'showFieldModsProgress',
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
                    {'label': _loc('SETTING_OPTION_ON', 'On')},
                    {'label': _loc('SETTING_ELITE_OPTION_CUSTOMIZATION_ONLY', 'Customization only')},
                    {'label': _loc('SETTING_OPTION_OFF', 'Off')},
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
            if key == 'showEliteProgress':
                config_key = 'eliteMode'
                new_value = _normalize_elite_mode(new_settings.get(key))
            elif key == 'showFieldModsProgress':
                config_key = 'fieldModsMode'
                new_value = _normalize_field_mods_mode(new_settings.get(key))
            elif key == 'showResearchMode':
                config_key = 'researchMode'
                new_value = _normalize_research_mode(new_settings.get(key))
            elif key == 'showUpgradesMode':
                config_key = 'upgradesMode'
                new_value = _normalize_upgrades_mode(new_settings.get(key))
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
